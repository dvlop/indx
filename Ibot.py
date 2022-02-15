# -*- coding: utf-8 -*-
from indxbot import Indx
import sqlite3
import os
import time
from datetime import datetime
from statistics import median

# сюда забиваем данны с биржи
login = ""
wmid = ""
password = ""
culture = "ru-RU"

stock_bot = Indx(login, wmid, password, culture)
id_list = {}

tools = stock_bot.get_tools()['value']
for tool in tools:
    id_list[tool['name']+'.' + tool['type']] = str(tool['id'])

# Пары, по которым собираемся торговать
PAIRS = {
    'ETH.ECU': {
        'ORDER_AMOUNT': '1',  # Сколько валюты 1 использовать в ордере ( в данном случае, 1 mETH),
        'ORDER_LIFE_TIME': 3,  #  через сколько минут отменять неисполненный ордер на покупку CURR_1
        'PROFIT_MARKUP_DOWN': 0.001,  # Какой навар нужен с каждой сделки при покупке (0.001 = 0.1%). Можно ставить 0
        'PROFIT_MARKUP_UP': 0.002,  # Какой навар нужен с каждой сделки при продаже  (0.002 = 0.2%)
        'MED_PRICE_PERIOD': 3,  # за какой период смотреть историю торгов (1 - 30 минут, 2 - 60 минут, 3 - 90 минут и т.д)
        'TRADE_PERCENT': 10, # допустимый процент отклонения текущей цены от максимальной цены за период
        'JUST_BUY': True # покупать без анализа торгов True - не анализировать, False - анализировать
                },
    # Новые пары писать ниже, по образцу
    }
CURR_DIR = os.path.dirname(os.path.abspath(__file__))

LOG_FILE = CURR_DIR + '/log.txt'

def log(*args):
    l = open(LOG_FILE, 'a')
    print(datetime.now(), *args)
    print(datetime.now(), *args, file=l)
    l.close()

# Свой класс исключений
class ScriptError(Exception):
    pass
class ScriptQuitCondition(Exception):
    pass



while True:
    try:
        conn = sqlite3.connect('lndx.db')
        cursor = conn.cursor()

        # Если не существует таблиц, их нужно создать (первый запуск)
        orders_q = """
          create table if not exists
            orders (
              order_type TEXT,
              order_pair TEXT,
              order_pair_id NUMERIC,
              
              buy_order_id NUMERIC,
              buy_initial_amount REAL,
              buy_initial_price REAL,
              buy_created DATETIME,
              buy_finished DATETIME,
              buy_cancelled DATETIME,

              sell_order_id NUMERIC,
              sell_amount REAL,
              sell_initial_price REAL,
              sell_created DATETIME,
              sell_finished DATETIME
            );
        """
        cursor.execute(orders_q)

        log("""
                             ~~~ Новый круг ~~~
            """)
        all_pairs = [pair for pair in PAIRS]

        stock_orders = stock_bot.get_open_orders()['value']
        all_stock_orders_id = [str(order['offerid']) for order in stock_orders]
        #raise SystemExit





        for pair in all_pairs:

            #offers = stock_bot.get_offers(id_list[pair])['value']
            #bid = offers[0]['price']
            #buy_amount = 1
            #new_order = stock_bot.create_order(id=str(id_list[pair]),
            #                                   count="{cr:0.0f}".format(cr=buy_amount),
            #                                   isbid='true',  # buy
            #                                   price="{cr:0.8f}".format(cr=bid - 0.1)
            #                                   )
            #print(new_order)
            #order = new_order['value']['OfferID']
            #time.sleep(2)
            #cancel = stock_bot.delete_order(order_id=str(order))
            #if cancel['code'] == 0 and cancel['value']['Code'] == 0:
            #print('delete ok')
            #continue

            log(f"              Работаем по паре {pair}")
            log(f"1. Получаем все неисполненные ордера из БД по паре: {pair}")

            orders_q = f"""
                SELECT
                    CASE WHEN order_type='buy' THEN buy_order_id ELSE sell_order_id END order_id,
                    order_type, 
                    order_pair,                    
                    sell_amount, 
                    sell_initial_price, 
                    strftime('%s',buy_created),
                    buy_initial_price,
                    order_pair_id
                FROM
                  orders
                WHERE
                  order_pair = '{pair}' AND
                  buy_cancelled IS NULL AND CASE WHEN order_type='buy' THEN buy_finished IS NULL ELSE sell_finished IS NULL END
            """
            orders_info = {}
            for row in cursor.execute(orders_q):
                orders_info[str(row[0])] = {'order_type': row[1], 'order_pair': row[2], 'sell_amount': row[3],
                                            'sell_initial_price': row[4], 'buy_created': row[5], 'curr_rate': row[6],
                                            'order_pair_id': row[7]
                                            }
            #если есть данные в базе
            if len(orders_info) > 0:
                log(f"2. Получены неисполненные ордера из БД по паре {pair}, проверяем биржу:", [order for order in orders_info])

                for order in orders_info:
                    log(f'2.1. Проверяем есть ли {order} в списке stock_order')
                    if order in all_stock_orders_id:
                        log(f'2.1.1. Ордер {order} есть в списке stock_order значит невыполнен, проверяем тип ордера')
                        if orders_info[order]['order_type'] == 'sell':
                            # 2.1.1.1. Еслли Селл переходим к следующему
                            continue

                        log(f'2.1.1.2. Ордер {order} - Бай проверяем давно ли висит')
                        order_created = int(orders_info[order]['buy_created'])
                        time_passed = time.time() - order_created
                        if time_passed > PAIRS[orders_info[order]['order_pair']]['ORDER_LIFE_TIME'] * 60:
                            log(f"2.1.1.2.1. Ордер {order} по покупку НЕ выполнен за {time_passed} секунд, отменяем")
                            cancel = stock_bot.delete_order(order_id=order)
                            if cancel['code'] == 0 and cancel['value']['Code'] == 0:
                                log("2.1.1.2.1.1 Ордер %s был успешно отменен" % order)
                                cursor.execute(
                                    """
                                      UPDATE orders
                                      SET
                                        buy_cancelled = datetime()
                                      WHERE
                                        buy_order_id = :buy_order_id

                                    """, {
                                        'buy_order_id': order
                                    }
                                )
                                conn.commit()
                            else:
                                log('2.1.1.2.1.2. Какие-то проблемы при отмене ордера', cancel)
                            # 2.1.1.2.2. Если недавно оставляем и переходим к новому ордеру
                    else:
                        log(f'2.1.2. Ордера {order} нет в списке stock_order - ордер выполнен ')

                        if orders_info[order]['order_type'] == 'sell':
                            log(f' 2.1.2.1.1. Ордер {order} - это СЕЛЛ. Записываем в базу')
                            cursor.execute(
                                """
                                  UPDATE orders
                                  SET
                                    sell_finished = datetime()
                                  WHERE
                                    sell_order_id = :sell_order_id

                                """, {
                                    'sell_order_id': order
                                }
                            )
                            conn.commit()
                        else:
                            log(f'2.1.2.1.2. Ордер {order} - БАЙ. Создаем селл')
                            # 2.1.2.1.2. Если бай - создаем Селл
                            new_order = stock_bot.create_order(id=str(orders_info[order]['order_pair_id']),
                                                               count="{cr:0.0f}".format(
                                                                   cr=orders_info[order]['sell_amount']),
                                                               isbid='false',  # sell
                                                               price="{cr:0.4f}".format(
                                                                   cr=orders_info[order]['sell_initial_price'])
                                                               )

                            sell_amount = orders_info[order]['sell_amount']
                            sell_initial_price = orders_info[order]['sell_initial_price']

                            if new_order['code'] == 0 and new_order['value']['OfferID'] > 0:
                                log("2.1.2.1.2.1. Создан ордер на продажу", new_order)
                                cursor.execute(
                                    """
                                      UPDATE orders
                                      SET
                                        order_type = 'sell',
                                        buy_finished = datetime(),
                                        sell_order_id = :sell_order_id,
                                        sell_created = datetime(),
                                        sell_amount = :sell_amount,
                                        sell_initial_price = :sell_initial_price
                                      WHERE
                                        buy_order_id = :buy_order_id
                                    """, {
                                        'buy_order_id': order,
                                        'sell_order_id': new_order['value']['OfferID'],
                                        'sell_amount': sell_amount,
                                        'sell_initial_price': sell_initial_price
                                    }
                                )
                                conn.commit()

                            else:
                                log("2.1.2.1.2.2. Не удалось создать ордер на продажу", new_order)

            else:
                log(f"2.2. Неисполненных ордеров по паре {pair} в БД нет. Переходим к следующей паре")

        log('3. Получаем из настроек все пары, по которым нет неисполненных ордеров')

        all_pairs = [pair for pair in PAIRS]

        orders_q = """
            SELECT
              distinct(order_pair) pair              
            FROM
              orders
            WHERE
              buy_cancelled IS NULL AND CASE WHEN order_type='buy' THEN buy_finished IS NULL ELSE sell_finished IS NULL END
        """
        for row in cursor.execute(orders_q):
            all_pairs.remove(row[0])

        if all_pairs:
            log('3.1. Найдены пары, по которым нет неисполненных ордеров:', all_pairs)
            for pair in all_pairs:
                log(f"4. Работаем с парой: {pair}")

                log(f"  Получаем текуще курсы по паре: {pair}")
                offers = stock_bot.get_offers(id_list[pair])['value']
                bid = offers[0]['price']
                ask = bid
                for offer in offers:
                    if offer['kind'] == 0:
                        ask = offer['price']
                        break
                log(f"""
                                bid (цена покупки): {bid}
                                ask (цена продажи): {ask}
                """)

                buy_price = ask
                if PAIRS[pair]['JUST_BUY']:
                    log("5.1 Покупка по текущей цене")

                else:
                    log("5.2. Покупка, с анализом торгов: получаем результаты последних торгов для определения цены")

                    call_api = stock_bot.get_history(id=id_list[pair])
                    trades = call_api['value']
                    buy_prices = []

                    for i in range(1, PAIRS[pair]['MED_PRICE_PERIOD']+1):
                            buy_prices.append(float(trades[-i]['max']))

                    if not buy_prices:
                        log('5.2.1. Не удалось получить цены продаж за период (не было сделок на покупку), пропускаем пару')
                        continue
                    else:
                        max_price = max(buy_prices)
                        trade_percent = 1

                        if ask > max_price*(1-PAIRS[pair]['TRADE_PERCENT']/100) and ask > trades[-1]['close']:
                            buy_price = ask

                        else:
                            log("""Текущая цена: {ask} не подходит под заданные условия:
                                     close_price: {cp}
                                     max_price: {max_price}
                                     {x}% max_price: {pc}""".format(
                                ask=ask,
                                cp=trades[-1]['close'],
                                max_price=max_price,
                                x=PAIRS[pair]['TRADE_PERCENT'],
                                pc=max_price*(1-PAIRS[pair]['TRADE_PERCENT']/100)

                            ))
                            continue

                curr_rate = buy_price - buy_price * float(PAIRS[pair]['PROFIT_MARKUP_DOWN'])
                buy_amount = float(PAIRS[pair]['ORDER_AMOUNT']) #/ curr_rate
                sell_amount = buy_amount
                sell_price = curr_rate + curr_rate * float( PAIRS[pair]['PROFIT_MARKUP_UP'])

                log(
                    'Цена покупки = %0.4f, с наценкой %s курс составит %0.4f'
                    %
                    (
                        buy_price,
                        PAIRS[pair]['PROFIT_MARKUP_DOWN'],

                        curr_rate
                    )
                )

                log(
                    """Итого собираемся купить:
                                %s: %0.0f по курсу %0.4f,
                                которые продадим по курсу %0.4f.
                            Итого на баланс упадет %0.8f %s
                       """
                    %
                    (
                        pair.split('.')[1],
                        buy_amount,
                        curr_rate,

                        sell_price,

                        sell_amount * sell_price - buy_amount * curr_rate,
                        pair.split('.')[0],
                    )
                )

                new_order = stock_bot.create_order(id=str(id_list[pair]),
                                                   count="{cr:0.0f}".format(cr = buy_amount),
                                                   isbid='true',  # buy
                                                   price="{cr:0.4f}".format(cr=curr_rate)
                                                   )

                print(new_order)
                if new_order['code'] == 0 and new_order['value']['OfferID'] > 0:
                    log("Создан ордер на покупку", new_order)
                    cursor.execute(
                        """
                          INSERT INTO orders(
                              order_type,
                              order_pair,
                              order_pair_id,
                              buy_order_id,
                              buy_initial_amount,
                              buy_initial_price,
                              buy_created,
                              sell_amount,
                              sell_initial_price

                          ) Values (
                            'buy',
                            :order_pair,
                            :order_pair_id,
                            :order_id,
                            :buy_order_amount,
                            :buy_initial_price,
                            datetime(),
                            :sell_amount,
                            :sell_initial_price
                          )
                        """, {
                            'order_pair': pair,
                            'order_pair_id': id_list[pair],
                            'order_id': new_order['value']['OfferID'],
                            'buy_order_amount': buy_amount,
                            'buy_initial_price': curr_rate,
                            'sell_amount': sell_amount,
                            'sell_initial_price': sell_price
                        }
                    )
                    conn.commit()
                else:
                    log("Не удалось создать ордер", new_order)

        else:
            log('3.2. По всем парам есть неисполненные ордера')

        # break
        time.sleep(5)
        log ("""
                            *** Конец ***
                
        """)

    except Exception as e:
        log(e)
    finally:
        conn.close()

