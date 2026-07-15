pf = 2.33
tp = 14.5
pt = 41.3
maxdd = 2.2
fee = 24837
netpnl = 54296

pe = tp + pt
pnl_fee = netpnl / fee
maxdd_dec = maxdd / 100.0
score = (pf * pe / 100 * pnl_fee) / (1 + maxdd_dec) * 100

print("PE:", pe)
print("PnL/Fee:", pnl_fee)
print("MaxDD dec:", maxdd_dec)
print("Score:", score)
