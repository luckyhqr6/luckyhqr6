import warnings
from enum import Enum, IntEnum

import pandas as pd
from dateutil.parser import parse
from math import ceil, floor

import plotly.tools as tls
import plotly.plotly as py
#import cufflinks as cf


class OptionType(Enum):
    Call = 0
    Put = 1


class OptionStatus(IntEnum):
    OTM = 0
    ITM = 1


class Position(IntEnum):
    Short = -1
    Long = 1


class OptionStrategy(object):
    def __init__(self, name='Strategy'):
        self.name = name
        self.options = {}

    def add(self, option):
        if option.ConId is None:
            option.ConId = -999
            warnings.warn('Option does not have an ConID!', UserWarning)
        if option.ConId in self.options.keys():
            option_hold = self.options[option.ConId]
            actual_position = option_hold.quantity * option_hold.position
            new_position = option.quantity * option.position
            if actual_position * new_position > 0:
                self.options[option.ConId].quantity += option.quantity
            else:
                self.options[option.ConId].quantity -= option.quantity

            if self.options[option.ConId].quantity < 0:
                self.options[option.ConId].quantity *= -1
                self.options[option.ConId].position = Position(option_hold.position * -1)
            elif self.options[option.ConId].quantity == 0:
                self.options.pop(option.ConId, None)
        else:
            self.options[option.ConId] = option

    def __str__(self):
        msg = ''
        for option in self.options.values():
            msg += str(option) + '\n'
        return msg[:-1]

    def get_option_from_ConId(self, ConId):
        return self.options[ConId]

    def profit_loss_at(self, price):
        value = 0
        for option in self.options.values():
            value += option.profit_loss_at(price)
        return value

    def _get_strike_range(self):
        strikes = [option.strike_price for option in self.options.values()]
        return [min(strikes), max(strikes)]

    def plot(self, plotly_folder=None):
        df = self._generate_strategy_dataframe()
        if plotly_folder is None:
            options_plot_name = '{}_options'.format(self.name)
            strategy_plot_name = '{}_strategy'.format(self.name)
        else:
            options_plot_name = '{}/{}_options'.format(plotly_folder, self.name)
            strategy_plot_name = '{}/{}_strategy'.format(plotly_folder, self.name)
        # Plot options profit/loss
        _ = df.ix[:, :len(self.options)].iplot(kind='scatter', width=2, colorscale="dflt", theme='ggplot',
                                               filename=options_plot_name, asUrl=True, world_readable=True)
        # Plot strategy profit/loss
        _ = df.ix[:, self.name].iplot(kind='scatter', width=2, colorscale="dflt", theme='ggplot',
                                      filename=strategy_plot_name, asUrl=True, world_readable=True)

    def _generate_strategy_dataframe(self, index_step=5):
        strategy_profit_loss = {}
        price_range = self._generate_price_range(index_step)
        for price in price_range:
            profit_loss = []
            for option in self.options.values():
                profit_loss.append(option.profit_loss_at(price))
            profit_loss.append(self.profit_loss_at(price))
            strategy_profit_loss[price] = profit_loss
        df = pd.DataFrame(strategy_profit_loss).transpose()
        col_names = self._generate_columns_names()
        df.columns = col_names
        return df

    def _generate_columns_names(self):
        col_names = []
        for option in self.options.values():
            name = '{}_{}_{}{}'.format(option.quantity, option.position.name,
                                       option.strike_price, option.option_type.name)
            col_names.append(name)
        col_names.append(self.name)
        return col_names

    def _generate_price_range(self, index_step):
        [lower_strike, upper_strike] = self._get_strike_range()
        if lower_strike < upper_strike:
            strike_range = upper_strike - lower_strike
            lower_price = floor(int(lower_strike - 0.2 * strike_range) / 10) * 10
            upper_price = ceil(int(upper_strike + 0.2 * strike_range) / 10) * 10
            price_range = range(lower_price, upper_price + index_step, index_step)
        else:
            raise NotImplementedError()
        return price_range


class OptionOperation(object):
    # region Constructors
    def __init__(self, position, premium, option_type, strike_price, con_id=None, underlying_asset=None, multiplier=1,
                 quantity=1, expiry=None):
        # Option properties
        self.option_type = option_type  # right
        self.strike_price = strike_price
        self.ConId = con_id
        self.underlying_asset = underlying_asset
        self.multiplier = multiplier
        self.expiry = expiry
        # Operation properties
        self.position = position
        self.premium = premium
        self.quantity = quantity


    def from_contract_description(cls, contracts: pd.DataFrame, position, premium, option_type=None,
                                  strike_price=None, underlying_asset=None, expiry=None, quantity=1):
        queries = []

        if option_type is not None:
            if option_type == OptionType.Call:
                queries.append("Right=='C'")
            elif option_type == OptionType.Put:
                queries.append("Right=='P'")

        if strike_price is not None:
            queries.append("Strike==" + str(strike_price))

        if underlying_asset is not None:
            queries.append("Symbol=='{}'".format(underlying_asset))

        if expiry is not None:
            queries.append("Symbol=='{}'".format(expiry))

        query = None
        for q in queries:
            if query is None:
                query = q
            else:
                query = query + " and " + q

        selected_contract = contracts.query(query)
        if selected_contract.shape[0] > 1:
            raise ValueError()
        else:
            return cls.from_ConId(contracts, selected_contract.index[0], position, premium, quantity)


    def from_ConId(cls, contracts: pd.DataFrame, ConID, position, premium, quantity=1):
        try:
            right = contracts.ix[ConID, 'Right']
        except KeyError:
            raise KeyError('The ConId does not exist in the contract JSON file.')

        if right == 'C':
            option_type = OptionType.Call
        elif right == 'P':
            option_type = OptionType.Put
        else:
            raise ValueError('The ConId is not an option.')

        con_id = ConID
        strike_price = contracts.ix[ConID, 'Strike']
        underlying_asset = contracts.ix[ConID, 'Symbol']
        expiry = str(contracts.ix[ConID, 'Expiry'])
        multiplier = contracts.ix[ConID, 'Multiplier']
        premium = premium * quantity * multiplier
        return cls(position, premium, option_type, strike_price, con_id, underlying_asset, multiplier, quantity,
                   expiry)

    # endregion

    def __str__(self):
        expiry = parse(self.expiry).strftime('%B-%y')
        return ("{} {} {} {} {} {} at {}"
                .format(self.quantity, self.position.name, self.underlying_asset, expiry,
                        self.option_type.name, self.strike_price, self.premium))

    def profit_loss_at(self, price):
        if self.option_type == OptionType.Call:
            if price <= self.strike_price:
                value = - self.premium
            else:
                value = (price - self.strike_price) * self.multiplier - self.premium
        elif self.option_type == OptionType.Put:
            if price >= self.strike_price:
                value = - self.premium
            else:
                value = (self.strike_price - price) * self.multiplier - self.premium
        return value * self.position.value * self.quantity

    def status_at(self, price):
        if ((self.option_type == OptionType.Call and price >= self.strike_price) or
                (self.option_type == OptionType.Put and price <= self.strike_price)):
            return OptionStatus.ITM
        else:
            return OptionStatus.OTM

    def intrinsic_value_at(self, price):
        if self.status_at(price) == OptionStatus.ITM:
            return abs(self.strike_price - price)
        else:
            return 0


    def is_Call(self):
        return self.option_type == OptionType.Call


    def is_Put(self):
        return self.option_type == OptionType.Put

    def is_ITM_at(self, price):
        return self.status_at(price)


if __name__ == '__main__':
    option_1 = OptionOperation(position=Position.Long, premium=0, option_type=OptionType.Put, strike_price=2120,
                               con_id=1, expiry='20160909')
    option_2 = OptionOperation(position=Position.Short, premium=0, option_type=OptionType.Put, strike_price=2140,
                               con_id=2, expiry='20160909')
    option_3 = OptionOperation(position=Position.Short, premium=0, option_type=OptionType.Call, strike_price=2140,
                               con_id=3, expiry='20160909')
    option_4 = OptionOperation(position=Position.Long, premium=0, option_type=OptionType.Call, strike_price=2160,
                               con_id=4, expiry='20160909')
    options = [option_1, option_2, option_3, option_4]

    adaptative_condor = OptionStrategy('AdaptativeCondor')
    for option in options:
        adaptative_condor.add(option)

    print(adaptative_condor)

    option_5 = OptionOperation(position=Position.Long, premium=0, option_type=OptionType.Call, strike_price=2140,
                               con_id=3, expiry='20160909')
    option_6 = OptionOperation(position=Position.Short, premium=0, option_type=OptionType.Call, strike_price=2160,
                               quantity=3, con_id=4, expiry='20160909')
    option_7 = OptionOperation(position=Position.Long, premium=0, option_type=OptionType.Call, strike_price=2180,
                               quantity=2, con_id=5, expiry='20160909')

    options = [option_5, option_6, option_7]

    for option in options:
        adaptative_condor.add(option)

    print(adaptative_condor)
    pass