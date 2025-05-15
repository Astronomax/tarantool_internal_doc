#!/usr/bin/env python3
import os
import re
import shutil
import subprocess
import sys
import time
from typing import List, Optional, Tuple

def get_commit_list(tarantool_path: str, start_commit: str) -> List[str]:
    """Получает список коммитов от start_commit до HEAD (новые сначала)"""
    os.chdir(tarantool_path)
    cmd = f"git rev-list {start_commit}..HEAD"
    result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
    commits = result.stdout.strip().split('\n')
    return [start_commit] + list(reversed(commits))

def checkout_commit(commit: str) -> None:
    """Переключается на указанный коммит и обновляет субмодули"""
    print(f"Checking out commit: {commit[:8]}")
    subprocess.run(f"git checkout {commit}",
        shell=True,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    subprocess.run("git submodule update --init --recursive",
        shell=True,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def prepare_test_dir(test_dir: str) -> None:
    """Подготавливает тестовую директорию (очищает или создаёт)"""
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

def silent_make(release_build_path: str) -> None:
    try:
        subprocess.run(
            "make",# -j$(nproc)", 
            shell=True, 
            check=True,
            cwd=release_build_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        raise RuntimeError("Ошибка при выполнении make")

def build_and_run(tarantool_path: str, test_dir: str) -> float:
    """Собирает проект и запускает тест, возвращая скорость ops/sec"""
    
    original_dir = os.getcwd()
    
    try:
        release_build_path = os.path.join(tarantool_path, "release-build")
        # Проверяем существование release-build
        if not os.path.exists(release_build_path):
            raise FileNotFoundError(f"Директория {release_build_path} не существует")

        # Собираем проект
        silent_make(release_build_path)
        
        time.sleep(3)

        # Подготавливаем тестовую директорию
        #prepare_test_dir(test_dir)
        #os.chdir(test_dir)
        
        # Запускаем тест (вывод теста оставляем видимым)
        tarantool_bin = os.path.join(release_build_path, "src/tarantool")
        test_script = os.path.join(tarantool_path, "perf/lua/1mops_write.lua")
        
        if not os.path.exists(test_script):
            raise FileNotFoundError(f"Тестовый скрипт {test_script} не найден")
                
        # Запускаем тест
        cmd = f"{tarantool_bin} -i {test_script} --nodes=1 --fibers=6000 --ops=1000000 --transaction=1 --warmup=10 --sync"
        print(cmd)

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        # Парсим результат
        output = result.stdout
        print(output)  # Выводим весь вывод для логов
        
        match = re.search(r"master average speed\s+(\d+)\s+ops/sec", output)
        if not match:
            raise ValueError("Не удалось найти скорость в выводе")
        
        return float(match.group(1))
    finally:
        # Всегда возвращаемся в исходную директорию
        os.chdir(original_dir)

def binary_search_perf_regression(commits: List[str], tarantool_path: str, test_dir: str, target_speed: float = 500000) -> Optional[Tuple[str, float]]:
    """Бинарный поиск коммита с падением производительности"""
    l = 0
    r = len(commits)
    
    while l + 1 < r:
        print(f"Диапазон поиска {l} - {r}")
        mid = (l + r) // 2
        commit = commits[mid]
        
        try:
            checkout_commit(commit)
            speed = build_and_run(tarantool_path, test_dir)
            
            if speed >= target_speed:
                print(f"Commit {commit[:8]} GOOD: {speed} ops/sec")
                l = mid
            else:
                print(f"Commit {commit[:8]} BAD: {speed} ops/sec")
                r = mid
                
        except Exception as e:
            print(f"Ошибка на коммите {commit[:8]}: {str(e)}", file=sys.stderr)
            sys.exit(1)
    
    return commits[mid]

def main():
    if len(sys.argv) != 3:
        print(f"Использование: {sys.argv[0]} <начальный_коммит> <путь_к_тарантулу>")
        print(f"Пример: {sys.argv[0]} a1b2c3d4 ~/dev/tarantool/")
        sys.exit(1)
    
    start_commit = sys.argv[1]
    tarantool_path = os.path.abspath(sys.argv[2])
    test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "work_dir")
    
    if not os.path.exists(tarantool_path):
        print(f"Ошибка: путь {tarantool_path} не существует")
        sys.exit(1)
    
    commits = get_commit_list(tarantool_path, start_commit)
    
    if not commits:
        print("Нет коммитов для проверки")
        return
    
    print(f"Всего коммитов для проверки: {len(commits)}")
    print(f"Тестовая директория: {test_dir}")
    

    print(f"Проверим, что первый коммит хороший")
    checkout_commit(commits[0])
    speed = build_and_run(tarantool_path, test_dir)
    assert(speed >= 500000)
    print(f"{speed} ops/sec")


    last_good_commit = binary_search_perf_regression(commits, tarantool_path, test_dir)
    last_good_commit_idx = commits.index(last_good_commit)
    
    if last_good_commit_idx == len(commits) - 1:
        print(f"Падение производительности не обнаружено")
    else:
        first_bad_commit = commits[commits.index(last_good_commit) + 1]
        print(f"Последний коммит с нормальной производительностью: {last_good_commit}")
        print(f"Первый коммит с низкой производительностью: {first_bad_commit}")

if __name__ == "__main__":
    main()
