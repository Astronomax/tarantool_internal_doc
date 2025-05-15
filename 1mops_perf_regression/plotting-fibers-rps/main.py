import os
import sys
import argparse
import subprocess
import re
import matplotlib.pyplot as plt

def drop_page_cache():
    """Очищает page cache используя sudo sync и echo 3"""
    try:
        print("Clearing page cache...")
        subprocess.run(['sudo', 'sync'], check=True)
        with open('/proc/sys/vm/drop_caches', 'w') as f:
            f.write('3\n')
        print("Page cache cleared successfully")
    except Exception as e:
        print(f"Error clearing page cache: {e}")

def run_tarantool_benchmark(tarantool_path, lua_script, fibers_range):
    results = []
    for fibers in fibers_range:
        # Очищаем кеш перед каждым запуском
        drop_page_cache()

        cmd = [
            tarantool_path,
            lua_script,
            f"--nodes=1",
            f"--fibers={fibers}",
            "--ops=1000000",
            "--transaction=1",
            "--warmup=10",
            "--sync"
        ]
        
        print(f"Running benchmark with {fibers} fibers...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout
        
        # Parse the output for average speed
        match = re.search(r"master average speed\s+(\d+)\s+ops/sec", output)
        if match:
            avg_speed = int(match.group(1))
            
            avg_speed = int(avg_speed / 1.16)
            
            results.append((fibers, avg_speed))
            print(f"Fibers: {fibers}, Avg speed: {avg_speed} ops/sec")
        else:
            print(f"Failed to parse output for fibers={fibers}")
    
    return results

def save_plot(results, filename=None):
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tarantool_benchmark_{timestamp}.png"
    
    fibers = [x[0] for x in results]
    speeds = [x[1] for x in results]
    
    plt.figure(figsize=(10, 6))
    plt.plot(fibers, speeds, 'o-')
    plt.title('Tarantool 1M OPS Write Benchmark')
    plt.xlabel('Number of Fibers')
    plt.ylabel('Average Speed (ops/sec)')
    plt.grid(True)
    
    # Сохраняем в текущую директорию
    plt.savefig(filename)
    print(f"\nGraph saved to: {os.path.abspath(filename)}")
    plt.close()  # Закрываем фигуру чтобы не показывалась на экране

def main():
    #parser = argparse.ArgumentParser(description='Run Tarantool 1M OPS benchmark with varying fiber counts')
    #parser.add_argument('tarantool_build_path', help='Path to Tarantool build directory')
    #args = parser.parse_args()
    #
    #tarantool_path = f"{args.tarantool_build_path}/src/tarantool"
    tarantool_path = f"/home/astronomax/dev/tarantool/release-build/src/tarantool"
    lua_script = "/home/astronomax/dev/tarantool/perf/lua/1mops_write.lua"
    
    # Generate fibers range from 1000 to 7000 with step 100
    fibers_range = range(1000, 7001, 50)
    
    results = run_tarantool_benchmark(tarantool_path, lua_script, fibers_range)
    
    save_plot(results, 'plot.jpg')

    print("\nResults:")
    for fibers, speed in results:
        print(f"{fibers}, {speed}")

if __name__ == "__main__":
    main()
