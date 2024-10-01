# txn

```lua
-- (src/lua/schema.lua)

local function box_begin_impl(options, level)
    ...
    if builtin.box_txn_begin() == -1 then -- int box_txn_begin(); (src/box/txn.h)
        box.error(box.error.last(), level + 1)
    end
    if timeout then
        assert(builtin.box_txn_set_timeout(timeout) == 0) -- int box_txn_set_timeout(double timeout); (src/box/txn.h)
    end
    if txn_isolation and
        internal.txn_set_isolation(txn_isolation) ~= 0 then
        box.rollback()
        box.error(box.error.last(), level + 1)
    end
    if is_sync then
        builtin.box_txn_make_sync() -- void box_txn_make_sync(); (src/box/txn.h)
    end
end
```
```c
/** (src/box/txn.h) */

static inline void
txn_set_timeout(struct txn *txn, double timeout)
{
	assert(timeout > 0);
	txn->timeout = timeout;
}

/**
 * Begin a transaction in the current fiber.
 *
 * A transaction is attached to caller fiber, therefore one fiber can have
 * only one active transaction.
 */
int
box_txn_begin(void)
{
	//...
	if (txn_begin() == NULL)
		return -1;
	txn_set_timeout(in_txn(), txn_timeout_default);
	return 0;
}

/**
 * Set @a timeout for transaction, when it expires, transaction
 * will be rolled back.
 */
int
box_txn_set_timeout(double timeout)
{
    //...
    struct txn *txn = in_txn();
    //...
	txn_set_timeout(txn, timeout);
	return 0;
}
```


