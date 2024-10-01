# ibuf

[ibuf](https://github.com/tarantool/small/blob/master/include/small/ibuf.h)  

**ibuf** - input buffer

```C
struct ibuf
{
	struct slab_cache *slabc;
	char *buf;
	/** Start of input. */
	char *rpos;
	/** End of useful input */
	char *wpos;
	/** End of buffer. */
	char *end;
	size_t start_capacity;
};
```

`char *ibuf::buf` - начало буффера  
  
`char *ibuf::rpos` - прочитанный префикс  
  
`char *ibuf::wpos` - конец участка данных  
  
`char *ibuf::end` - конец буффера

`buf` <**consumed**> `rpos` <**unconsumed (used)**> `wpos` <**unallocated (unused)**> `end`

```c
void
ibuf_create(struct ibuf *ibuf, struct slab_cache *slabc, size_t start_capacity)
```
\- инициализирует `ibuf`, но не аллоцирует в нем память под буффер

```c
void
ibuf_destroy(struct ibuf *ibuf);
```
\- освобождает память под буффером

```c
void
ibuf_reinit(struct ibuf *ibuf)
```
\- `ibuf_destroy` + `ibuf_create`

```c
static inline size_t
ibuf_used(struct ibuf *ibuf)
```
\- `wpos` - `rpos` (записано, но пока не прочитано)

```c
static inline size_t
ibuf_unused(struct ibuf *ibuf)
```
\- `end` - `wpos` (сколько ещё можно записать)

```c
static inline size_t
ibuf_capacity(struct ibuf *ibuf)
```
\- `end` - `buf`

```c
void *
ibuf_reserve_slow(struct ibuf *ibuf, size_t size)
```
\- вызывается только если на суффиксе не хватает места (unallocated < size), при этом если можно сдвинуть все в начало (выкинув consumed) так, чтобы после этого в конце оказалось достаточно свободного места, то обходимся этим, иначе переаллоцируем в 2 раза больший кусок памяти, и переносим всё туда. (для аллокаций используется slab аллокатор)

```c
void
ibuf_shrink(struct ibuf *ibuf);
```
\- `shrink_to_fit` в `std::vector`

```c
static inline void *
ibuf_reserve(struct ibuf *ibuf, size_t size)
```
\- проверяет достаточно ли свободного места в конце, если нет вызывает `ibuf_reserve_slow`.

```c
static inline void *
ibuf_alloc(struct ibuf *ibuf, size_t size)
```
\- продвинуть `wpos` вперед на `size`, т.е. чтобы что-то положить в `ibuf`, сначала зовется `ibuf_alloc`, затем руками в конец кладется то, что хочется.

```c
static inline void
ibuf_discard(struct ibuf *ibuf, size_t size)
```
\- выкинуть `size` байт с конца. Важно чтобы это была не обработанная (unconsumed) память.  
  
```c
static inline void
ibuf_truncate(struct ibuf *ibuf, size_t used)
```
\- выкинуть все, что еще не было прочитано.  
  
```c
static inline void
ibuf_consume(struct ibuf *ibuf, size_t size)
```
\- прочитать `size` байт с конца (сдвинуть `rpos` вперед на `size` байт)
