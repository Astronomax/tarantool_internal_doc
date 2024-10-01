# evio_service

[evio_service](https://github.com/tarantool/tarantool/blob/master/src/lib/core/evio.h)

**evio_service** - 

```c
struct evio_service_entry {
	/** Bind URI */
	struct uri uri;
	/** Interface/port to bind to */
	union {
		struct sockaddr addr;
		struct sockaddr_storage addrstorage;
	};
	socklen_t addr_len;
	/** IO stream context. */
	struct iostream_ctx io_ctx;
	/** libev io object for the acceptor socket. */
	struct ev_io ev;
	/** Pointer to the root evio_service, which contains this object */
	struct evio_service *service;
};
```

```c
static int
evio_setsockopt_keepalive(int fd)
```

```c
/** Set common client socket options. */
int
evio_setsockopt_client(int fd, int family, int type)
```

```c
int
evio_setsockopt_server(int fd, int family, int type)
```

```c
/**
 * A callback invoked by libev when acceptor socket is ready.
 * Accept the socket, initialize it and pass to the on_accept
 * callback.
 */
static void
evio_service_entry_accept_cb(ev_loop *loop, ev_io *watcher, int events)
```

```c
/*
 * Check if the UNIX socket exists and no one is
 * listening on it. Unlink the file if it's the case.
 */
static int
evio_service_entry_reuse_addr(const struct uri *u)
```

```c
/**
 * Try to bind on the configured port.
 *
 * Throws an exception if error.
 */
static int
evio_service_entry_bind_addr(struct evio_service_entry *entry)
```

```c
/**
 * Listen on bounded port.
 *
 * @retval 0 for success
 */
static int
evio_service_entry_listen(struct evio_service_entry *entry)
```

```c
static void
evio_service_entry_create(struct evio_service_entry *entry,
			  struct evio_service *service)
```

```c
/**
 * Try to bind.
 */
static int
evio_service_entry_bind(struct evio_service_entry *entry, const struct uri *u)
```

```c
static void
evio_service_entry_detach(struct evio_service_entry *entry)
```

```c
/** It's safe to stop a service entry which is not started yet. */
static void
evio_service_entry_stop(struct evio_service_entry *entry)
```

```c
static void
evio_service_entry_attach(struct evio_service_entry *dst,
			 const struct evio_service_entry *src)
```

```c
/** Recreate the IO stream contexts from the service entry URI. */
static int
evio_service_entry_reload_uri(struct evio_service_entry *entry)
```

```c
static inline int
evio_service_reuse_addr(const struct uri_set *uri_set)
```

```c
static void
evio_service_create_entries(struct evio_service *service, int size)
```

```c
void
evio_service_create(struct ev_loop *loop, struct evio_service *service,
		    const char *name, evio_accept_f on_accept,
		    void *on_accept_param)
```

```c
void
evio_service_attach(struct evio_service *dst, const struct evio_service *src)
```

```c
void
evio_service_detach(struct evio_service *service)
```

```c
/** Listen on bound socket. */
static int
evio_service_listen(struct evio_service *service)
```

```c
void
evio_service_stop(struct evio_service *service)
```

```c
/** Bind service to specified URI. */
static int
evio_service_bind(struct evio_service *service, const struct uri_set *uri_set)
```

```c
int
evio_service_start(struct evio_service *service, const struct uri_set *uri_set)
```

```c
int
evio_service_reload_uris(struct evio_service *service)
```
