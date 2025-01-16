def find_closest_line(lines, price):
    closest_line_index = min(range(len(lines)), key=lambda i: abs(lines[i] - price))
    closest_line = lines[closest_line_index]
    distanceOfClosestLine = price - closest_line
    return [closest_line_index, closest_line, distanceOfClosestLine]


def the_two_lines(lines, nearst_line):
    if nearst_line[2] > 0 and nearst_line[0] < len(lines) - 1:
        #print("the channel is : "+str(nearst_line[1]), "  and  " ,str(lines[nearst_line[0]+1]))
        return nearst_line[1] , lines[nearst_line[0]+1]

    elif nearst_line[2] < 0 and nearst_line[0] > 0:
        #print("the channel is : " , str(nearst_line[1]) , "  and  " , str(lines[nearst_line[0] -1]))
        return nearst_line[1] , lines[nearst_line[0] - 1]
    else:
        #print("the channel is : ",str(nearst_line[1]))
        return "one_line_error"
def signal(lines,price):
    center = (lines[1]+lines[0])/2
    y=0
    if price > center :
        m1 = 100/(lines[1]-center)
        y = m1*(price-center)
    elif price<center :
        m2 = 100/(center-lines[0])
        y = m2 * (price - center)
    return y

def execute_trade(price, Rsi, nearst_line,last_state,BB,lines,W,last_order_price):
    response = None
    orderprice =None

    if last_order_price and last_state == "buy":
        profit_or_loss = ((price - last_order_price) / last_order_price) * 100
        if profit_or_loss <= -100 or profit_or_loss >= 100:
            response = "sellSL"
            return [response]

    two_lines = the_two_lines(lines,nearst_line)
    RSI_Signal = ((50-Rsi)*2)/100

    if two_lines !="one_line_error" :
        lines_Signal =signal(two_lines,price)/100
    else :
        lines_Signal =0

    BB_Signal = signal([BB["Bollinger_Upper"],BB["Bollinger_Lower"]],price)/100


    s=(W[0]*BB_Signal+W[1]*RSI_Signal+W[2]*lines_Signal)/sum(W)
    #print(f"lines signal is : {lines_Signal:.4f} ", f"RSI signal : {RSI_Signal} ", f"BB signal : {BB_Signal}","s :",s)
    # شرط خرید
    if (W[0]*BB_Signal+W[1]*RSI_Signal+W[2]*lines_Signal)/sum(W) >= 0.9 and last_state == "sell":
        #response = place_order("buy", ticker, amount, last_price+0.005)

        response = "buy"
        orderprice=price
    # شرط فروش

    elif (W[0]*BB_Signal+W[1]*RSI_Signal+W[2]*lines_Signal)/sum(W) <= -0.85 and last_state == "buy":

        #response = place_order("sell", ticker, coin-0.01, last_price+0.006)

        response = "sell"

    # به‌روزرسانی پورتفولیو


    return [response,orderprice]


