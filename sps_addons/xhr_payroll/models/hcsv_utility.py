# -*- coding: utf-8 -*-

from odoo import api, fields, models
from num2words import num2words

VIETNAMESE_DATE_FORMAT = 'Ngày %d tháng %m năm %Y'
DATE_FORMAT = '%d-%m-%Y'


class HcsvUtility(models.TransientModel):
    _name = 'hcsv.utility'

    @staticmethod
    def convert_amount_to_words(currency, amount, decimal_places=0):
        """
        :param currency (res.currency)
        :param amount (int or float)
        :param decimal_places (int)
        :return:
        """
        amount = ('{0:.%sf}' % decimal_places).format(float(amount))
        if not currency:
            return ''
        if currency.name == 'VND':
            amount = int(float(amount))
            return num2words(amount, lang='vi_VN') + ' đồng'
        else:
            amount = float(amount)
            return num2words(amount, lang='vi_VN') + ' ' + currency.currency_unit_label

    @staticmethod
    def format_number(number, decimal_places=2, thousand_separators=True, escape_zero=True, escape_int=True):
        """
        number: float or int - the number need to be format
        decimal_places: int - the numbers of digit in decimal part
        thousand_separators: boolean - use thousand separators or not
        escape_zero: boolean - return '0' instead of '' when number is 0 or False
        escape_int: boolean - return integer number or float number with trailing zero number after '.' character
        """
        if str(number) == '0':
            return '0' if escape_zero else ''
        try:
            if thousand_separators:
                price_str = ('{0:,.%sf}' % decimal_places).format(float(number))
            else:
                price_str = ('{0:.%sf}' % decimal_places).format(float(number))
        except ValueError as e:
            return number
        if '.' in price_str:  # number contain decimal part
            decimal_parts = price_str.split('.')[-1]
        else:
            decimal_parts = False
        if not decimal_parts or all([dpr == '0' for dpr in decimal_parts]):  # is integer number
            if escape_int or decimal_places == 0:
                return price_str.split('.')[0]
            else:
                return price_str.split('.')[0] + '.' + '0' * decimal_places
        decimal_parts_reverse = decimal_parts[::-1]
        first_none_zero_number_index = [idx for idx, dpr in enumerate(decimal_parts_reverse) if dpr != '0']
        if first_none_zero_number_index:
            first_none_zero_number_index = first_none_zero_number_index[0]
            decimal_parts_reverse = decimal_parts_reverse[first_none_zero_number_index:]
            decimal_part = decimal_parts_reverse[::-1]
            decimal_part += '0' * decimal_places
            decimal_part = decimal_part[:decimal_places]
            price_str_parts = price_str.split('.')
            price_str_parts[-1] = decimal_part
            price_str = '.'.join(price_str_parts)
        return price_str

    @staticmethod
    def add_currency_symbol_to_number(currency, number):
        """
        :param currency: (res.currency) res.currency object
        :param number: (str) number in string
        :return:
        """
        if currency.position == 'before':
            return '%s %s' % (currency.symbol, number)
        else:
            return '%s %s' % (number, currency.symbol)

    @staticmethod
    def format_number_with_currency(currency, number, decimal_places=2, thousand_separators=True, escape_zero=True, escape_int=True):
        """
            all parameters are combined from format_number and add_currency_symbol_to_number function
        """
        format_number = HcsvUtility.format_number(number, decimal_places, thousand_separators, escape_zero, escape_int)
        format_number_with_currency_symbol = HcsvUtility.add_currency_symbol_to_number(currency, format_number)
        return format_number_with_currency_symbol

    @staticmethod
    def is_int(val):
        try:
            int(val)
            return True
        except ValueError:
            return False

    @staticmethod
    def format_date_vn(date_obj):
        if not date_obj:
            return ''
        return date_obj.strftime('%d-%m-%Y')
