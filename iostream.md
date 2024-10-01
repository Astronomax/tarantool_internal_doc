# iostream

[iostream](https://github.com/tarantool/tarantool/blob/master/src/lib/core/iostream.h)

**iostream** - input/output stream

`iostream` - это абстрактный класс, в тарантуле пока только одна реализация: `plain_iostream` (просто зовет `read` и `write` из `socket.h`). Это сделано, чтобы писать какие-то реализации, которые инкапсулируют какую-нибудь сериализацию/десериализацию в `read`, `write`.

```C
struct iostream_vtab {
	/** Destroys implementation-specific data. */
	void
	(*destroy)(struct iostream *io);
	/** See iostream_read. */
	ssize_t
	(*read)(struct iostream *io, void *buf, size_t count);
	/** See iostream_write. */
	ssize_t
	(*write)(struct iostream *io, const void *buf, size_t count);
	/** See iostream_writev. */
	ssize_t
	(*writev)(struct iostream *io, const struct iovec *iov, int iovcnt);
};
```

```C
/**
 * An IO stream implements IO operations over a file descriptor.
 * Can be used to add some data processing transparently to the user.
 */
struct iostream {
	const struct iostream_vtab *vtab;
	/** Implementation specific data. */
	void *data;
	/** File descriptor used for IO. Set to -1 on destruction. */
	int fd;
	/** Bitwise combination of iostream_flag. */
	unsigned flags;
};
```

```C
/**
 * A negative status code is returned by an iostream read/write operation
 * in case it didn't succeed.
 */
enum iostream_status {
	/** IO error. Diag is set. */
	IOSTREAM_ERROR = -1,
	/**
	 * IOSTREAM_WANT_READ and IOSTREAM_WANT_WRITE are returned if
	 * the operation would block trying to read or write data from
	 * the fd. Diag is not set in this case. The caller is supposed
	 * to poll/select the fd if this status code is returned.
	 *
	 * Note, a read is allowed to return IOSTREAM_WANT_WRITE and
	 * a write is allowed to return IOSTREAM_WANT_READ, because
	 * the underlying protocol may do some sort of server-client
	 * negotiation under the hood. Use iostream_status_to_events
	 * to convert the status to libev events.
	 */
	IOSTREAM_WANT_READ = -2,
	IOSTREAM_WANT_WRITE = -3,
};
```

**Замечание:** `write` и `read` могут быть реализованы так, что `read` может вернуть `IOSTREAM_WANT_WRITE`, а `write` - `IOSTREAM_WANT_READ`.


```C
/** Possible values of iostream::flags. */
enum iostream_flag {
	/**
	 * Set if the iostream is encrypted (e.g. with SSL/TLS).
	 */
	IOSTREAM_IS_ENCRYPTED = 1 << 0,
};
```

```c
static inline int  
iostream_status_to_events(ssize_t status)
```
\- возвращает `libev` события, соответствующие статусу.
  
`IOSTREAM_WANT_READ` → `EV_READ`  
  
`IOSTREAM_WANT_WRITE` → `EV_WRITE`  
предполагается, что ничего другого на вход придти не может  

```c
static inline void  
iostream_clear(struct iostream *io)
```
\- обнуляет `iostream`, но не освобождает файловый дискриптор

```c
static inline void  
iostream_move(struct iostream *dst, struct iostream *src)
```
\- move-конструктор

```c
void  
iostream_close(struct iostream *io);
```
\- уничтожает объект `iostream`, освобождает файловый дискриптор (зовет `shutdown`, `close`)

```C
enum iostream_mode {
	/** Uninitilized context (see iostream_ctx_clear). */
	IOSTREAM_MODE_UNINITIALIZED = 0,
	/** Server connection (accept). */
	IOSTREAM_SERVER,
	/** Client connection (connect). */
	IOSTREAM_CLIENT,
};

struct ssl_iostream_ctx;

/**
 * Context used for creating IO stream objects of a particular type.
 */
struct iostream_ctx {
	/** IO stream mode: server or client. */
	enum iostream_mode mode;
	/**
	 * Context used for creating encrypted streams. If it's NULL, then
	 * streams created with this context will be unencrypted.
	 */
	struct ssl_iostream_ctx *ssl;
};
```

**Замечание:** `ibuf` и `obuf` выгодно использовать по 2 на каждое соединение. Тогда можно будет освободить весь буффер целиком, не нужно будет сдвигать блок в начало и прочее. Пишем в один буффер, когда он закончится, пишем во второй. Далее ждем, пока данные в первом буффере перестанут быть полезными и освобождаем этот буффер целиком. Таким образом, получается, что размер такого составного буффера как-бы равен размеру одного, в том смысле, что в составном буффере нет места только если в него записано как минимум {размер одного буффера + 1} необработанных байт. Этот прием используется в `iproto_connection`.

