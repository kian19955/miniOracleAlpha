"""split_order_by_market_liquidity: If True, the order request will be split by market liquidity (based on the qty of the asset at the specified price)"""
#             split_order_by_market_liquidity: bool = False,
def _split_order_by_market_liquidity(self, ord_req: OrderRequest, exec_price: float) -> OrderRequest:
    if ord_req.type == OrderType.LIMIT:
        return ord_req

    order_book: DataFrame = fetch_order_book(
        ord_req.symbol)  # Level 0: 'Bids' or 'Asks', Level 1: 'Price' or 'Quantity'

    if ord_req.direction == PositionDirection.LONG:  # TODO: Check for open and closing positions as well to make it compatible with close_pos
        levels = order_book.loc['Asks']
        matched = levels[levels['Price'] <= exec_price]
    else:
        levels = order_book.loc['Bids']
        matched = levels[levels['Price'] >= exec_price]

    available_qty = matched['Quantity'].sum()
    taker_qty = min(available_qty, ord_req.qty)
    maker_qty = ord_req.qty - taker_qty

    if maker_qty <= 0:
        return ord_req

    maker_order = OrderRequest.modify_order_request(
        ord_req,
        create_copy=True,
        qty=maker_qty
    )
    self.portfolio.add_order_request(maker_order)

    taker_order = OrderRequest.modify_order_request(
        ord_req,
        create_copy=True,
        qty=taker_qty
    )
    logger.info(
        f"Splitting order {ord_req.uuid} into taker: {taker_order.uuid}(qty={taker_order.qty}) and maker: {maker_order.uuid}(qty={maker_order.qty})")
    return taker_order
