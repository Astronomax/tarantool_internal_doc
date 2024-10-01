# iproto_connection

[iproto_connection](https://github.com/tarantool/tarantool/blob/be34a844733f6fa579f367901c6cb30cbbcfeea0/src/box/iproto.cc#L753)

**iproto_connection** - iproto соединение

```C
/**
 * ibuf structure:
 *                   rpos             wpos           end
 * +-------------------|----------------|-------------+
 * \________/\________/ \________/\____/
 *  \  msg       msg /    msg     parse
 *   \______________/             size
 *   response is sent,
 *     messages are
 *      discarded
 */
struct iproto_connection
{
	/**
	 * Два сменяющих друг друга входных буффера (rotating buffers).
	 * Как только один из буфферов оказывается заполненным полностью,
	 * переходим ко второму. Если оба буффера оказываются заполенными,
	 * ввод приостанавливается. Для этого в структуре есть поле `in_stop_list`.
	 * `iproto_check_msg_max(struct iproto_thread *iproto_thread)` проверяет,
	 * не превышен ли у данного треда `struct iproto_thread` лимит сообщений
	 * `unsigned iproto_readahead = 16320`, которые в данный момент находятся в
	 * обработке. Если лимит превышен, вызывается
	 * `iproto_connection_stop_msg_max_limit(struct iproto_connection *con)`,
	 * который приостанавливает обработку текущего соединения (останавливает
	 * `ev_io iproto_connection::input` и добавляет соединение в
	 * `rlist iproto_thread::stopped_connections`). Буфферы заполняются
	 * данными, которые приходят по сети снаружи от пользователя
	 * (из `iostream iproto_connection::io`).
	 */
	struct ibuf ibuf[2];
	/** Указатель на текущий буффер. */
	struct ibuf *p_ibuf;
	/**
	 * Количество необработанных сообщений в каждом из буфферов.
	 * Инкрементируется всякий раз, когда
	 * `iproto_enqueue_batch(struct iproto_connection *con, struct ibuf *in)
	 * удается распарсить очередной запрос из текущего буффера `p_ibuf`.
	 * Каждый раз, когда `iproto_enqueue_batch` успешно парсит следующий запрос
	 * `size_t iproto_connection::parse_size` уменьшается на тот объем памяти,
	 * которую занимал закодированный запрос. При этом возможно, что после этого
	 * `size_t iproto_connection::parse_size` останется ненулевым.
	 */
	size_t input_msg_count[2];
	/**
	 * Два сменяющих друг друга выходных буффера (rotating buffers).
	 * Вращает буфферы "tx"-тред, потому что он же в них и пишет.
	 * Как только "iproto"-тред записал какую-то часть данных из буффера
	 * в `iostream iproto_connection::io`, он передает в "tx" позицию, до
	 * которой записал. В "tx"-треде в методе
	 * `tx_accept_wpos(struct iproto_connection *con, const struct iproto_wpos *wpos)`
	 * эта позиция обрабатывается, и в соответствии с новой позицией,
	 * выбирается буффер для следующей записи (`con->tx.p_obuf`).
	 * Алгоритм выбора буффера простой. Если wpos указывает на текущий буффер,
	 * значит, что второй буффер уже полностью записался, поэтому он выбирается
	 * в качестве буффера для следущей записи `con->tx.p_obuf`.
	 */
	struct obuf obuf[2];
	/**
	 * Позиция в выходном буффере, которая указывает на начало данных,
	 * которые ожидают записи в `iostream iproto_connection::io`. Сдвигается
	 * в "iproto"-треде при каждой успешной записи.
	 */
	struct iproto_wpos wpos;
	/**
	 * Позиция в выходном буффере, которая указывает на конец данных, которые
	 * ожидают записи в `iostream iproto_connection::io`. Сдвигается
	 * "iproto"-тредом, когда он получает от "tx" сообщение о том,
	 * что в буффер были записаны ещё какие-то данные. (`iproto_msg::wpos`).
	 */
	struct iproto_wpos wend;
	/*
	 * Размер данных, которые ещё не были распаршены, то есть часть запроса,
	 * который пока что не был полностью прочитан. `ibuf.wpos - parse_size`
	 * всегда указывает на начало недопаршенного запроса. Это защищает нас от
	 * возможной релокации `ibuf` или ротации буфферов.
	 */
	size_t parse_size;
	/**
	 * Number of active long polling requests that have already
	 * discarded their arguments in order not to stall other
	 * connections.
	 */
	int long_poll_count;
	/**
	 * I/O stream used, который используется непосредственно для записи и
	 * чтения данных из сокета.
	 */
	struct iostream io;
	struct ev_io input;
	struct ev_io output;
	/** Logical session. */
	struct session *session;
	ev_loop *loop;
	/**
	 * Pre-allocated disconnect msg. Is sent right after
	 * actual disconnect has happened. Does not destroy the
	 * connection. Used to notify existing requests about the
	 * occasion.
	 */
	struct cmsg disconnect_msg;
	/**
	 * Pre-allocated destroy msg. Is sent after disconnect has
	 * happened and a last request has finished. Firstly
	 * destroys tx-related resources and then deletes the
	 * connection.
	 */
	struct cmsg destroy_msg;
	/**
	 * Connection state. Mainly it is used to determine when
	 * the connection can be destroyed, and for debug purposes
	 * to assert on a double destroy, for example.
	 */
	enum iproto_connection_state state;
	struct rlist in_stop_list;
	/**
	 * Flag indicates, that client sent SHUT_RDWR or connection
	 * is closed from client side. When it is set to false, we
	 * should not write to the socket.
	 */
	bool can_write;
	/**
	 * Hash table that holds all streams for this connection.
	 * This field is accessible only from iproto thread.
	 */
	struct mh_i64ptr_t *streams;
	/**
	 * Kharon is used to implement box.session.push().
	 * When a new push is ready, tx uses kharon to notify
	 * iproto about new data in connection output buffer.
	 *
	 * Kharon can not be in two places at the time. When
	 * kharon leaves tx, is_push_sent is set to true. After
	 * that new pushes can not use it. Instead, they set
	 * is_push_pending flag. When Kharon is back to tx it
	 * clears is_push_sent, checks is_push_pending and departs
	 * immediately back to iproto if it is set.
	 *
	 * This design makes it easy to use a single message per
	 * connection for pushes while new pushes do not wait for
	 * the message to become available.
	 *
	 * iproto                                               tx
	 * -------------------------------------------------------
	 *                                        + [push message]
	 *                 <--- notification ----
	 *                                        + [push message]
	 * [feed event]
	 *             --- kharon travels back ---->
	 * [write to socket]
	 *                                        + [push message]
	 *                                        [new push found]
	 *                 <--- notification ----
	 * [write ends]
	 *                          ...
	 */
	struct iproto_kharon kharon;
	/**
	 * The following fields are used exclusively by the tx thread.
	 * Align them to prevent false-sharing.
	 */
	struct {
		alignas(CACHELINE_SIZE)
		/** Pointer to the current output buffer. */
		struct obuf *p_obuf;
		/** True if Kharon is in use/travelling. */
		bool is_push_sent;
		/**
		 * True if new pushes are waiting for Kharon
		 * return.
		 */
		bool is_push_pending;
		/** List of inprogress messages. */
		struct rlist inprogress;
	} tx;
	/** Authentication salt. */
	char salt[IPROTO_SALT_SIZE];
	/** Iproto connection thread */
	struct iproto_thread *iproto_thread;
	/**
	 * The connection is processing replication command so that
	 * IO is handled by relay code.
	 */
	bool is_in_replication;
	/** Link in iproto_thread->connections. */
	struct rlist in_connections;
	/** Set if connection is being dropped. */
	bool is_drop_pending;
	/**
	 * Generation is sequence number of dropping connection invocation.
	 *
	 * See also `struct iproto_drop_finished`.
	 */
	unsigned drop_generation;
	/**
	 * Messaged sent to TX to cancel all inprogress requests of the
	 * connection.
	 */
	struct cmsg cancel_msg;
	/** Set if connection is accepted in TX. */
	bool is_established;
};
```

```c
static void
tx_accept_wpos(struct iproto_connection *con, const struct iproto_wpos *wpos)
```
 \- Обновляет указатель на текущий доступный для записи буффер `obuf *iproto_connection::p_obuf`. Вызывается в "tx"-треде всякий раз, когда "tx"-тред "узнает" о том, что "iproto" тред записал все данные из буфферов `obuf *iproto_connection::p_obuf` вплоть до `wpos`.

```c
static void
net_end_join(struct cmsg *m)
```
\- завершает `join` в "iproto"-треде. Используется, как последнее сообщение в `iproto_thread::join_route`:
```c
iproto_thread->join_route[0] =
	{ tx_process_replication, &iproto_thread->net_pipe };
iproto_thread->join_route[1] = { net_end_join, NULL };
```
Выставляет `con->is_in_replication = false`, затем вызывает `iproto_enqueue_batch`, чтобы продолжить читать данные из сокета. Даже если `iproto_enqueue_batch` не сможет вычитать ни одного запроса, он как минимум вызовет `iproto_connection_feed_input`, поэтому соединение никогда не повиснет.
```c
static void
iproto_msg_finish_input(iproto_msg *msg)
```
\- завершаем обработку очередного сообщения. Декрементируем счетчик сообщений (`con->input_msg_count[msg->p_ibuf == &con->ibuf[1]]`) для того буффера, на который указывает данное сообщение (буффер, из которого данное сообщение было прочитано). Как только счетчик дошел до нуля, можно пометить соответствующий префикс буффера, как "consumed". Замечание: нельзя это делать по чуть-чуть для каждого сообщения, потому что порядок, в котором сообщения лежат в буффере и порядок, в котором на этих сообщениях вызывается `iproto_msg_finish_input`, различаются. Соответственно, если сообщение указывает на тот буффер, который сейчас не используется, то он просто полностью освобождается. Иначе если сообщение указывает на тот же буффер, на который указывает `iproto_connection::p_ibuf`, то буффер освобождается не полностью, освобождается все кроме суффикса размера `iproto_connection::parse_size`. При этом важное замечание: `iproto_msg_finish_input` не пытается обновлять `iproto_connection::p_ibuf`, это происходит в другом месте в методе `iproto_connection_input_buffer`.

```c
static struct ibuf *
iproto_connection_input_buffer(struct iproto_connection *con)
```
\- Если нет места для чтения ввода, мы можем сделать одно из
 следующее:

 \- попробовать получить новый `ibuf`. Постоянное получение нового входного буфера при отсутствии свободного места делает нас уязвимыми для атак с переполнением входных данных. Поэтому в одном соединении используется не более 2 `ibuf`, один из которых "открыт", получая входные данные, а другой закрыт, ожидая сброса вывода из соответствующего `obuf`.

 \- остановить ввод и подождать, пока клиент прочитает накопленный вывод, чтобы можно было повторно использовать входной буфер. Остановить ввод безопасно только в том случае, если известно, что есть вывод. В этом случае поток входных событий возобновится, когда будут отправлены все ответы на предыдущие запросы. Поскольку имеется два буфера, ввод прекращается только тогда, когда оба они полностью израсходованы.

Чтобы эта стратегия работала, каждый используемый `ibuf` должен соответствовать хотя бы одному запросу. В противном случае в обоих `obuf` может не оказаться данных для сброса, а текущий `ibuf` слишком мал, чтобы вместить большой входящий запрос.

TODO: здесь еще есть о чем рассказать, например, иногда блок памяти размера `con::parse_size` копируется из одного буффера в другой.

```c
static struct iproto_connection *
iproto_connection_new(struct iproto_thread *iproto_thread)
```
\- создает новое соединение в треде `iproto_thread`. Вызывается из `iproto_thread_accept`.
```c
	con->input.data = con->output.data = con;
	ev_io_init(&con->input, iproto_connection_on_input, -1, EV_NONE);
```

```c
static inline void
iproto_connection_feed_input(struct iproto_connection *con)
```
\- Сигнализирует о том, что нужно прочитать из сокета следующую порцию данных, только если соединение не заблокировано на вводе-выводе (`!ev_is_active(&con->input)`), не остановлено (`rlist_empty(&con->in_stop_list)`) или не находится в репликации (`con->is_in_replication == false`).

```c
	if (!ev_is_active(&con->input) && rlist_empty(&con->in_stop_list) &&
	    !con->is_in_replication)
		ev_feed_event(con->loop, &con->input, EV_CUSTOM);
```
`iproto_connection` берет на себя ответственность самостоятельно сигнализировать в нужные моменты времени о том, что нужно запланировать чтение следующего блока данных из сокета. Именно для этого вызывается `iproto_connection_feed_input`. При этом не важно, есть ли сейчас какие-то доступные для чтения данные в сокере или нет. Если в дальшейшем при попытке прочитать что-то в коллбеке `iproto_connection_on_input` окажется, что никаких новых данных в сокете пока нет, `iproto_connection_on_input` сам подпишется на события чтения/записи этого сокета, чтобы в конечном счете удовлетворить это намерение на получение новых данных от `iproto_connection`. Если окажется, что полученных данных недостаточно для того, чтобы прочитать из них очередной запрос, `iproto_enqueue_batch` сам вызовет `iproto_connection_feed_input`. Может получиться так, что данные в сокет сыпятся намного быстрее, чем для них освобождается место в буфферах `iproto_connection::ibuf`, размер которых хочется удерживать в каких-то пределах, чтобы они не разрастались черезмерно. Данная стратегия позволяет следить за этим.

```c
static void
iproto_connection_on_input(ev_loop *loop, struct ev_io *watcher,
			   int /* revents */)
```
\- коллбек вотчера `ev_io iproto_connection::input`. Пытается прочитать новую порцию данных из сокета во входной буффер `con::ibuf`.
```c
	ssize_t nrd = iostream_read(io, in->wpos, ibuf_unused(in));
	if (nrd < 0) {                  /* Socket is not ready. */
		if (nrd == IOSTREAM_ERROR)
			goto error;
		int events = iostream_status_to_events(nrd);
		if (con->input.events != events) {
			ev_io_stop(loop, &con->input);
			ev_io_set(&con->input, con->io.fd, events);
		}
		ev_io_start(loop, &con->input);
		return;
	}
```
Если оказывается, что никаких доступных данных в сокете пока нет, `iproto_connection_on_input` сам подпишется на события чтения/записи этого сокета.
Если что-то прочитать удалось, вызывается `iproto_enqueue_batch`, который пытается распарсить очередной запрос. Следующий вызов коллбека `iproto_connection_on_input` будет запланирован либо в `iproto_enqueue_batch`, либо при обработке выходного потока в `iproto_connection_on_output`.

```c
static inline int
iproto_enqueue_batch(struct iproto_connection *con, struct ibuf *in)
```
\- в цикле парсит запросы из буффера `ibuf`. После вызова `iproto_enqueue_batch`, очевидно, `con->parse_size` не обязательно окажется 0, часто будет получаться так, что в буффере будет оставаться какой-то префикс следующего запроса, который `iproto_enqueue_batch` начал парсить, но не закончил, т.к. ему не хватило данных. На первый взгляд, не зная, как именно парсятся эти запросы, может показаться, что в `iproto_enqueue_batch` есть некоторая брешь в производительности. А именно, может получиться так, что один запрос может разбиться на очень маленькие блоки, и каждый раз, получая очередной блок, `iproto_enqueue_batch` будет безуспешно пытаться распарсить этот запрос, не сохраняя при этом прогресс, состояние парсера, и мы таким образом будем парсить одно и то же несколько раз. На самом деле такой проблемы нет, просто потому что этот самый стейт очень мал, в нем всего 3 состояния:
- в буффере не достаточно байт, чтобы распарсить длину запроса, которая идет первой.
- длину запроса удалось прочитать, но объем данных в буффере оказался меньше, чем эта самая длина запроса.
- длину запроса удалось прочитать, при этом в буффере достаточно данных, для того чтобы распарсить очередной запрос.

Тело запроса начинает по-настоящему парситься только после того, как было достигнуто последнее состояние. Поэтому прогресс, который мы рискуем потерять не значительный. Гораздо дешевле будет снова прочитать одно число и сравнить его в объемом доступных данных, чем прикручивать какую-то логику по хранению этого прогресса.

Сам `iproto_enqueue_batch` для каждого успешно прочитанного запроса вызывает `iproto_msg_prepare`, который производит окончательную инициализацию сообщения `iproto_msg`, в том числе вызывает `iproto_msg_decode`, который окончательно разбирает тело запроса, и в зависимости от типа запроса, выставляет соответствующий `cmsg_hop *cmsg::route`.

