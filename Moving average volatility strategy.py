""" 2020.09.25  15:27
@zp
数据端，既用到了153数据库，也用到了Tushare Pro数据库
显然，加入的条件过多，必定导致过拟合问题，(由于未留出测试集，因此，可以肯定的是过拟合问题存在，但却无法量化验证)

"""
# coding=utf-8
import math
import tushare as ts
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import talib
import pandas as pd
from datetime import datetime, date
import seaborn as sns
sns.set(style="darkgrid", palette="muted", color_codes=True)
from scipy import stats,integrate
#%matplotlib inline
sns.set(color_codes=True)
matplotlib.rcParams['axes.unicode_minus']=False
plt.rcParams['font.sans-serif']=['SimHei']

ts.set_token('fbe180aa0a1b06ef2e64e6f5a2d8f11ca1fab6fc4857e2ccf7e271eb')
pro = ts.pro_api()
#读取数据的时间范围
star="20070602"
end="20220105"
df = pro.index_daily( ts_code='000300.SH', start_date=star, end_date=end)
df=df.sort_index(ascending=False)#排序
df.index=pd.to_datetime(df.trade_date,format='%Y-%m-%d')#设置日期序列索引
df_close=df.close/df.close[0]#计算净值

df.trade_date=None
for i in range(20,len(df.index)):#计算20天的波动率
    df.trade_date[i]=np.std(np.log(df_close[i-20:i] /df_close[i-20:i].shift(-1)))*np.sqrt(252)*100#波动率计算
df1=df.trade_date.dropna()


t=20#一20天为时间段计算波动率
T=100#波动率移动平均时间段。
df1=pd.Series(df1,dtype=float)#转换类型
df2= talib.MA(pd.Series(  pd.Series(df.trade_date.dropna() ,dtype=np.float) ), timeperiod=T)
sig=pd.Series(0,df1.index)
for i in range(math.ceil(T/t), math.floor(len(df1)/t)-1):#信号判断
     if df1[i*t+t]<df2[i*t+t] and  df1[i*t]>df1[i*t+t]:#这里可以作为检验，即去掉if  查看波动
        for j in range(i*t+1,(i+1)*t+1):
            sig[j]=1
df_close=df_close.sort_index()
ret=(df_close-df_close.shift(1))/df_close.shift(1)
ret1=ret.tail(len(df1)).sort_index()*sig
cum=np.cumprod(ret1+1).dropna()
cum=cum.tail(len(cum)-T-2)#组合累计净值


def bj_standard(code,lab='沪深300指数',col='k'):#针对沪深股票，直接画出比较基准（收益情况）
    standard_base = pro.index_daily( ts_code=code, start_date=star, end_date=end)
    standard_base=standard_base.head(len( standard_base)-T-20)
    standard_base=standard_base.sort_index()
    standard_base.index=pd.to_datetime(standard_base.trade_date,format='%Y-%m-%d')#设置日期索引
    close_base= standard_base.close
    standard_ret=standard_base.change/standard_base.close.shift(-1)
    standard_sig=pd.Series(0,index=close_base.index)
    standard_trade=standard_sig.shift(1).dropna()/100#shift(1)整体下移一行
    standard_SmaRet=standard_ret*standard_trade.dropna()
    standard_cum=np.cumprod(1+standard_ret[standard_SmaRet.index[0:]])-1
    plt.plot(close_base/close_base[-1],label=lab,color=col)
    return close_base/close_base[-1] #standard_cum
###########################################################################

def Tongji(cum):
    cum=cum.sort_index()
    NH=(cum[-1]-1)*100*252/len(cum.index)
    BD=np.std(np.log(cum/cum.shift(-1)))*np.sqrt(252)*100
    SR=(NH-4)/BD
    return_list=cum
    MHC=((np.maximum.accumulate(return_list) - return_list) / np.maximum.accumulate(return_list)).max()*100
    print("年化收益率：{:.2f}%:，年化夏普率：{:.2f},波动率为：{:.2f}%,最大回撤：{:.2f}%".format( NH,SR,BD,MHC))
Tongji(cum)
############################################################################
if __name__=="__main__":
    bj_standard('000300.SH')
    plt.plot(cum,label="策略组合净值",color='r',linestyle='-')
    plt.title("策略净值走势图")
    plt.legend()

