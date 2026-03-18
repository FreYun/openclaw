import tushare as ts
ts.set_token('ed396239156fa590b3730414be7984b029e021c3531e419f6bc170d4')
pro = ts.pro_api()

# 查 167301.OF 基本信息
basic = pro.fund_basic(ts_code='167301.OF')
print('167301.OF 基本信息:')
print(basic)
