"""Auto-generated file, do not edit by hand. AR metadata"""
from ..phonemetadata import NumberFormat, PhoneNumberDesc, PhoneMetadata

PHONE_METADATA_AR = PhoneMetadata(id='AR', country_code=54, international_prefix='00',
    general_desc=PhoneNumberDesc(national_number_pattern='[1-368]\\d{9}|9\\d{10}', possible_number_pattern='\\d{6,11}'),
    fixed_line=PhoneNumberDesc(national_number_pattern='11\\d{8}|(?:2(?:2(?:[013]\\d|2[13-79]|4[1-6]|5[2457]|6[124-8]|7[1-4]|8[13-6]|9[1267])|3(?:1[467]|2[03-6]|3[13-8]|[49][2-6]|5[2-8]|[067]\\d)|4(?:7[3-8]|9\\d)|6(?:[01346]\\d|2[24-6]|5[15-8])|80\\d|9(?:[0124789]\\d|3[1-6]|5[234]|6[2-46]))|3(?:3(?:2[79]|6\\d|8[2578])|4(?:[78]\\d|0[0124-9]|[1-35]\\d|4[24-7]|6[02-9]|9[123678])|5(?:[138]\\d|2[1245]|4[1-9]|6[2-4]|7[1-6])|6[24]\\d|7(?:[0469]\\d|1[1568]|2[013-9]|3[145]|5[14-8]|7[2-57]|8[0-24-9])|8(?:[013578]\\d|2[15-7]|4[13-6]|6[1-357-9]|9[124]))|670\\d)\\d{6}', possible_number_pattern='\\d{6,10}', example_number='1123456789'),
    mobile=PhoneNumberDesc(national_number_pattern='675\\d{7}|9(?:11[2-9]\\d{7}|(?:2(?:2[013]|3[067]|49|6[01346]|80|9[147-9])|3(?:36|4[12358]|5[138]|6[24]|7[069]|8[013578]))[2-9]\\d{6}|\\d{4}[2-9]\\d{5})', possible_number_pattern='\\d{6,11}', example_number='91123456789'),
    toll_free=PhoneNumberDesc(national_number_pattern='800\\d{7}', possible_number_pattern='\\d{10}', example_number='8001234567'),
    premium_rate=PhoneNumberDesc(national_number_pattern='60[04579]\\d{7}', possible_number_pattern='\\d{10}', example_number='6001234567'),
    shared_cost=PhoneNumberDesc(national_number_pattern='NA', possible_number_pattern='NA'),
    personal_number=PhoneNumberDesc(national_number_pattern='NA', possible_number_pattern='NA'),
    voip=PhoneNumberDesc(national_number_pattern='NA', possible_number_pattern='NA'),
    pager=PhoneNumberDesc(national_number_pattern='NA', possible_number_pattern='NA'),
    uan=PhoneNumberDesc(national_number_pattern='810\\d{7}', possible_number_pattern='\\d{10}', example_number='8101234567'),
    emergency=PhoneNumberDesc(national_number_pattern='1(?:0[017]|28)', possible_number_pattern='\\d{3}', example_number='101'),
    voicemail=PhoneNumberDesc(national_number_pattern='NA', possible_number_pattern='NA'),
    no_international_dialling=PhoneNumberDesc(national_number_pattern='810\\d{7}', possible_number_pattern='\\d{10}', example_number='8101234567'),
    national_prefix='0',
    national_prefix_for_parsing='          0?(?:            (11|             2(?:               2(?:                 02?|                 [13]|                 2[13-79]|                 4[1-6]|                 5[2457]|                 6[124-8]|                 7[1-4]|                 8[13-6]|                 9[1267]               )|               3(?:                 02?|                 1[467]|                 2[03-6]|                 3[13-8]|                 [49][2-6]|                 5[2-8]|                 [67]               )|               4(?:                 7[3-578]|                 9               )|               6(?:                 [0136]|                 2[24-6]|                 4[6-8]?|                 5[15-8]               )|               80|               9(?:                 0[1-3]|                 [19]|                 2\\d|                 3[1-6]|                 4[02568]?|                 5[2-4]|                 6[2-46]|                 72?|                 8[23]?               )            )|            3(?:              3(?:                2[79]|                6|                8[2578]              )|              4(?:                0[124-9]|                [12]|                3[5-8]?|                4[24-7]|                5[4-68]?|                6[02-9]|                7[126]|                8[2379]?|                9[1-36-8]              )|              5(?:                1|                2[1245]|                3[237]?|                4[1-46-9]|                6[2-4]|                7[1-6]|                8[2-5]?              )|              6[24]|              7(?:                1[1568]|                2[15]|                3[145]|                4[13]|                5[14-8]|                [069]|                7[2-57]|                8[126]              )|              8(?:                [01]|                2[15-7]|                3[2578]?|                4[13-6]|                5[4-8]?|                6[1-357-9]|                7[36-8]?|                8[5-8]?|                9[124]              )            )          )15        )?',
    national_prefix_transform_rule=u'9\\1',
    number_format=[NumberFormat(pattern='([68]\\d{2})(\\d{3})(\\d{4})', format=u'\\1-\\2-\\3', leading_digits_pattern=['[68]'], national_prefix_formatting_rule=u'0\\1'),
        NumberFormat(pattern='(9)(11)(\\d{4})(\\d{4})', format=u'\\2 15-\\3-\\4', leading_digits_pattern=['911'], national_prefix_formatting_rule=u'0\\1'),
        NumberFormat(pattern='(9)(\\d{3})(\\d{3})(\\d{4})', format=u'\\2 15-\\3-\\4', leading_digits_pattern=['9(?:2[234689]|3[3-8])', '9(?:2(?:2[013]|3[067]|49|6[01346]|80|9[147-9])|3(?:36|4[12358]|5[138]|6[24]|7[069]|8[013578]))', '9(?:2(?:2[013]|3[067]|49|6[01346]|80|9(?:[17-9]|4[13479]))|3(?:36|4[12358]|5(?:[18]|3[014-689])|6[24]|7[069]|8(?:[01]|3[013469]|5[0-39]|7[0-2459]|8[0-49])))'], national_prefix_formatting_rule=u'0\\1'),
        NumberFormat(pattern='(9)(\\d{4})(\\d{3})(\\d{3})', format=u'\\2 15-\\3-\\4', leading_digits_pattern=['93[58]', '9(?:3(?:53|8[78]))', '9(?:3(?:537|8(?:73|88)))'], national_prefix_formatting_rule=u'0\\1'),
        NumberFormat(pattern='(9)(\\d{4})(\\d{2})(\\d{4})', format=u'\\2 15-\\3-\\4', leading_digits_pattern=['9[23]'], national_prefix_formatting_rule=u'0\\1'),
        NumberFormat(pattern='(11)(\\d{4})(\\d{4})', format=u'\\1 \\2-\\3', leading_digits_pattern=['1'], national_prefix_formatting_rule=u'0\\1'),
        NumberFormat(pattern='(\\d{3})(\\d{3})(\\d{4})', format=u'\\1 \\2-\\3', leading_digits_pattern=['2(?:2[013]|3[067]|49|6[01346]|80|9[147-9])|3(?:36|4[12358]|5[138]|6[24]|7[069]|8[013578])', '2(?:2[013]|3[067]|49|6[01346]|80|9(?:[17-9]|4[13479]))|3(?:36|4[12358]|5(?:[18]|3[0-689])|6[24]|7[069]|8(?:[01]|3[013469]|5[0-39]|7[0-2459]|8[0-49]))'], national_prefix_formatting_rule=u'0\\1'),
        NumberFormat(pattern='(\\d{4})(\\d{3})(\\d{3})', format=u'\\1 \\2-\\3', leading_digits_pattern=['3(?:53|8[78])', '3(?:537|8(?:73|88))'], national_prefix_formatting_rule=u'0\\1'),
        NumberFormat(pattern='(\\d{4})(\\d{2})(\\d{4})', format=u'\\1 \\2-\\3', leading_digits_pattern=['[23]'], national_prefix_formatting_rule=u'0\\1')],
    intl_number_format=[NumberFormat(pattern='([68]\\d{2})(\\d{3})(\\d{4})', format=u'\\1-\\2-\\3', leading_digits_pattern=['[68]']),
        NumberFormat(pattern='(9)(11)(\\d{4})(\\d{4})', format=u'\\1 \\2 \\3-\\4', leading_digits_pattern=['911']),
        NumberFormat(pattern='(9)(\\d{3})(\\d{3})(\\d{4})', format=u'\\1 \\2 \\3-\\4', leading_digits_pattern=['9(?:2[234689]|3[3-8])', '9(?:2(?:2[013]|3[067]|49|6[01346]|80|9[147-9])|3(?:36|4[12358]|5[138]|6[24]|7[069]|8[013578]))', '9(?:2(?:2[013]|3[067]|49|6[01346]|80|9(?:[17-9]|4[13479]))|3(?:36|4[12358]|5(?:[18]|3[014-689])|6[24]|7[069]|8(?:[01]|3[013469]|5[0-39]|7[0-2459]|8[0-49])))']),
        NumberFormat(pattern='(9)(\\d{4})(\\d{3})(\\d{3})', format=u'\\2 15-\\3-\\4', leading_digits_pattern=['93[58]', '9(?:3(?:53|8[78]))', '9(?:3(?:537|8(?:73|88)))']),
        NumberFormat(pattern='(9)(\\d{4})(\\d{2})(\\d{4})', format=u'\\1 \\2 \\3-\\4', leading_digits_pattern=['9[23]']),
        NumberFormat(pattern='(11)(\\d{4})(\\d{4})', format=u'\\1 \\2-\\3', leading_digits_pattern=['1']),
        NumberFormat(pattern='(\\d{3})(\\d{3})(\\d{4})', format=u'\\1 \\2-\\3', leading_digits_pattern=['2(?:2[013]|3[067]|49|6[01346]|80|9[147-9])|3(?:36|4[12358]|5[138]|6[24]|7[069]|8[013578])', '2(?:2[013]|3[067]|49|6[01346]|80|9(?:[17-9]|4[13479]))|3(?:36|4[12358]|5(?:[18]|3[0-689])|6[24]|7[069]|8(?:[01]|3[013469]|5[0-39]|7[0-2459]|8[0-49]))']),
        NumberFormat(pattern='(\\d{4})(\\d{3})(\\d{3})', format=u'\\1 \\2-\\3', leading_digits_pattern=['3(?:53|8[78])', '3(?:537|8(?:73|88))']),
        NumberFormat(pattern='(\\d{4})(\\d{2})(\\d{4})', format=u'\\1 \\2-\\3', leading_digits_pattern=['[23]'])])
