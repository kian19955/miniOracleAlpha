def BBW_plugin(BBW,response):
    if BBW<10 and BBW>0.000 :
        response = response
    else :
        response = [None,response[1]]
    return  response