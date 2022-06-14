"""
@dazip

"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, date
from statsmodels.regression import linear_model
import statsmodels.api as sm

import threading
from queue import Queue
import math
import tushare as ts
import matplotlib
import talib
import seaborn as sns
sns.set(style="darkgrid", palette="muted", color_codes=True)
from scipy import stats,integrate
#%matplotlib inline
sns.set(color_codes=True)
matplotlib.rcParams['axes.unicode_minus']=False
plt.rcParams['font.sans-serif'] = ['SimHei']         # 中文显示
plt.rcParams['axes.unicode_minus'] = False   # 用来正常显示负号

code1="000001.SH"
code2="000012.SH"

#freq=65
def momentum(freq=65,test_start="20100101",test_end="20201001",t1=5,t2=10,t3=15,t4=20,t5=25,n=1):
    #读取数据
    def dataread():
        ts.set_token('fbe180aa0a1b06ef2e64e6f5a2d8f11ca1fab6fc4857e2ccf7e271eb')#需要获取token码https://tushare.pro/register?reg=385920
        pro = ts.pro_api()
        df_stock=pro.index_daily(ts_code=code1,  start_date=test_start, end_date=test_end, fields='close,trade_date')
        df_bond=df=pro.index_daily(ts_code=code2,start_date=test_start, end_date=test_end , fields='trade_date,close')
        return df_stock,df_bond
    df_stock,df_bond=dataread()
    #计算均值，时间为t1  t2  t3  t4
    def mean(t):
        df_stock.index=pd.to_datetime(df_stock.trade_date)
        return df_stock.close.sort_index().rolling(window=t).mean()

    def ret_base():
        df_stock.index=pd.to_datetime(df_stock.trade_date)
        df_bond.index =pd.to_datetime(df_bond.trade_date)
        ret_stock=(df_stock.close-df_stock.close.shift(-1))/df_stock.close.shift(-1)
        ret_bond= (df_bond.close- df_bond.close.shift(-1))/df_bond.close.shift(-1)
        return ret_stock,ret_bond.sort_index()

    def ret_same_time(x):
        return x[x.index>=mean(max(t1,t2,t3,t4,t5)).dropna().index[0] ]
    ret_stock=ret_same_time(ret_base()[0]).sort_index()#ret_base()[0][ret_base()[0].index>=mean(max(t1,t2,t3,t4,t5)).dropna().index[0] ]
    ret_bond= ret_same_time(ret_base()[1] )#ret_base()[1][ret_base()[1].index>=mean(max(t1,t2,t3,t4,t5)).dropna().index[0] ]
    DF=ret_same_time(df_stock.close).sort_index()

    mean1=ret_same_time(mean(t1))
    mean2=ret_same_time(mean(t2))
    mean3=ret_same_time(mean(t3))
    mean4=ret_same_time(mean(t4))
    mean5=ret_same_time(mean(t5))
    def sig_fun():
        sig_stock=pd.Series(0,ret_stock.index )
        sig_bond= pd.Series(0,ret_bond.sort_index().index)
        for i in range(math.ceil(len(ret_stock)/freq)-1):
            if DF[i*freq]>n*mean1[i*freq] and DF[i*freq]>n*mean2[i*freq] and DF[i*freq]>n*mean3[i*freq] and DF[i*freq]>n*mean4[i*freq] and DF[i*freq]>n*mean5[i*freq]:
                for j in range(i*freq,(1+i)*freq):
                    sig_stock[j]=1
                    sig_bond[j]=0
            else:
                for j in range(i*freq,(i+1)*freq):
                    sig_stock[j]=0
                    sig_bond[j]=1
        for i in range(freq*(math.ceil(len(ret_stock)/freq)-1),len(ret_bond)):
            k=freq*(math.ceil(len(ret_stock)/freq)-1)
            if DF[k]>mean1[k] and DF[k]>mean2[k] and DF[k]>mean3[k] and DF[k]>mean4[k] and DF[k]>mean5[k]:
                sig_stock[i]=1
                sig_bond[i]=0
            else:
                sig_stock[i]=0
                sig_bond[i]=1
        return sig_stock,sig_bond
    sig_stock,sig_bond=sig_fun()

    ret=(ret_stock*sig_stock+ret_bond*sig_bond) .sort_index()
    #cum=np.cumprod(1+ret.tail(len(ret)-1))

    def ret_port( ret_bond,ret_stock):
        ret=ret_bond*sig_bond+ret_stock*sig_stock
        ret=ret.sort_index().dropna()
        ret_stock=ret_stock.sort_index()
        ret_bond =ret_bond.sort_index()
        cum_bond=np.cumprod(1+ret_bond)
        cum_stock=np.cumprod(1+ret_stock)
        cum=np.cumprod(1+ret)
        return cum,cum_stock,cum_bond,ret
    cum,cum_stock,cum_bond,ret=ret_port( ret_bond,ret_stock)
    #画图
    def plot():
        plt.plot(cum_bond ,label="000012.SH",color='k',linestyle='-')
        plt.plot(cum_stock,label="000300.SH",color='b',linestyle='-')
        plt.plot(cum,label=" 组合策略（freq=65,[50,70,90,110,130]） ",color='darkred',linestyle='-')
        plt.title("净值走势")
        plt.legend(loc="upper left")
    #结果描述统计
    def performance(port_ret):
        port_ret=port_ret.sort_index(ascending=True)
        first_date = port_ret.index[0]
        final_date = port_ret.index[-1]
        time_interval = (final_date - first_date).days * 250 / 365
        # calculate portfolio's indicator
        nv = (1 + port_ret).cumprod()
        arith_mean = port_ret.mean() * 250
        geom_mean = (1 + port_ret).prod() ** (250 / time_interval) - 1
        sd = port_ret.std() * np.sqrt(250)
        mdd = ((nv.cummax() - nv) / nv.cummax()).max()
        sharpe = (geom_mean - 0) / sd
        calmar = geom_mean / mdd
        result = pd.DataFrame({'算术平均收益': [arith_mean], '几何平均收益': [geom_mean], '波动率': [sd],
                                   '最大回撤率': [mdd], '夏普比率': [sharpe], '卡尔曼比率': [calmar]})
        print (result)
    return plot(),performance(ret)
if __name__=="__main__":
    momentum(freq=65,test_start="20041201",test_end="20201001",t1=50,t2=70,t3=90,t4=110,t5=130,n=1)
