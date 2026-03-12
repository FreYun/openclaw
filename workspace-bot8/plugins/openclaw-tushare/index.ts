/**
 * Tushare Financial Data Plugin for OpenClaw
 * Provides tools to query Tushare Pro API for A-share market data,
 * financial statements, northbound capital flows, and more.
 */

import type { OpenClawPluginApi } from "openclaw/plugin-sdk";

const TUSHARE_API_URL = "https://api.tushare.pro";

async function callTushare(
  token: string,
  apiName: string,
  params: Record<string, unknown>,
  fields?: string,
): Promise<string> {
  const body: Record<string, unknown> = {
    api_name: apiName,
    token,
    params,
  };
  if (fields) {
    body.fields = fields;
  }

  const resp = await fetch(TUSHARE_API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
  }

  const json = (await resp.json()) as {
    code: number;
    msg: string;
    data?: { fields: string[]; items: unknown[][] };
  };

  if (json.code !== 0) {
    throw new Error(`Tushare API error (${json.code}): ${json.msg}`);
  }

  if (!json.data || !json.data.fields || !json.data.items) {
    return "No data returned.";
  }

  const { fields: cols, items } = json.data;
  if (items.length === 0) {
    return "Query returned 0 rows.";
  }

  // Format as CSV-style text for the LLM
  const header = cols.join("\t");
  const rows = items.map((row) => row.join("\t")).join("\n");
  return `${header}\n${rows}\n\n[${items.length} rows]`;
}

export default function register(api: OpenClawPluginApi) {
  const cfg = api.pluginConfig as { token?: string } | undefined;
  const token = cfg?.token ?? "";

  if (!token) {
    api.logger.warn("Tushare plugin: no token configured. All tools will fail.");
  }

  // ── Stock List ──────────────────────────────────────────────────────────────
  api.registerTool({
    name: "tushare_stock_basic",
    label: "Tushare Stock List",
    description:
      "Query A-share stock list from Tushare. Returns ts_code, symbol, name, area, industry, list_date, etc. " +
      "Use exchange='SSE' for Shanghai, 'SZSE' for Shenzhen. list_status: L=listed, D=delisted, P=paused.",
    parameters: {
      type: "object",
      properties: {
        ts_code: { type: "string", description: "Tushare stock code e.g. 600000.SH" },
        name: { type: "string", description: "Stock name (fuzzy match)" },
        exchange: { type: "string", description: "Exchange: SSE | SZSE | BSE" },
        list_status: { type: "string", description: "L=listed, D=delisted, P=paused (default L)" },
        market: { type: "string", description: "Market type: 主板|创业板|科创板|北交所" },
      },
      additionalProperties: false,
    },
    async execute(_id, params) {
      try {
        const p: Record<string, unknown> = {};
        if (params.ts_code) p.ts_code = params.ts_code;
        if (params.name) p.name = params.name;
        if (params.exchange) p.exchange = params.exchange;
        if (params.list_status) p.list_status = params.list_status;
        if (params.market) p.market = params.market;
        const text = await callTushare(
          token,
          "stock_basic",
          p,
          "ts_code,symbol,name,area,industry,market,list_date,list_status",
        );
        return { content: [{ type: "text", text }], details: {} };
      } catch (e) {
        return { content: [{ type: "text", text: `Error: ${e}` }], details: {} };
      }
    },
  });

  // ── Daily Quotes ────────────────────────────────────────────────────────────
  api.registerTool({
    name: "tushare_daily",
    label: "Tushare Daily Quotes",
    description:
      "Get daily OHLCV price data for A-shares. Returns open, high, low, close, vol, amount, pct_chg, change. " +
      "Provide ts_code for single stock or trade_date (YYYYMMDD) for market snapshot. " +
      "start_date/end_date for date range (YYYYMMDD).",
    parameters: {
      type: "object",
      properties: {
        ts_code: { type: "string", description: "Stock code e.g. 000001.SZ" },
        trade_date: { type: "string", description: "Trading date YYYYMMDD" },
        start_date: { type: "string", description: "Start date YYYYMMDD" },
        end_date: { type: "string", description: "End date YYYYMMDD" },
      },
      additionalProperties: false,
    },
    async execute(_id, params) {
      try {
        const p: Record<string, unknown> = {};
        if (params.ts_code) p.ts_code = params.ts_code;
        if (params.trade_date) p.trade_date = params.trade_date;
        if (params.start_date) p.start_date = params.start_date;
        if (params.end_date) p.end_date = params.end_date;
        const text = await callTushare(
          token,
          "daily",
          p,
          "ts_code,trade_date,open,high,low,close,change,pct_chg,vol,amount",
        );
        return { content: [{ type: "text", text }], details: {} };
      } catch (e) {
        return { content: [{ type: "text", text: `Error: ${e}` }], details: {} };
      }
    },
  });

  // ── Daily Basic (Valuation) ─────────────────────────────────────────────────
  api.registerTool({
    name: "tushare_daily_basic",
    label: "Tushare Daily Valuation",
    description:
      "Get daily valuation and market metrics: PE, PB, PS, market cap (total_mv, circ_mv), " +
      "turnover_rate, volume_ratio, free_float shares. Essential for valuation screening.",
    parameters: {
      type: "object",
      properties: {
        ts_code: { type: "string", description: "Stock code e.g. 600519.SH" },
        trade_date: { type: "string", description: "Trading date YYYYMMDD" },
        start_date: { type: "string", description: "Start date YYYYMMDD" },
        end_date: { type: "string", description: "End date YYYYMMDD" },
      },
      additionalProperties: false,
    },
    async execute(_id, params) {
      try {
        const p: Record<string, unknown> = {};
        if (params.ts_code) p.ts_code = params.ts_code;
        if (params.trade_date) p.trade_date = params.trade_date;
        if (params.start_date) p.start_date = params.start_date;
        if (params.end_date) p.end_date = params.end_date;
        const text = await callTushare(
          token,
          "daily_basic",
          p,
          "ts_code,trade_date,pe,pe_ttm,pb,ps,ps_ttm,total_mv,circ_mv,turnover_rate,turnover_rate_f,volume_ratio",
        );
        return { content: [{ type: "text", text }], details: {} };
      } catch (e) {
        return { content: [{ type: "text", text: `Error: ${e}` }], details: {} };
      }
    },
  });

  // ── Income Statement ─────────────────────────────────────────────────────────
  api.registerTool({
    name: "tushare_income",
    label: "Tushare Income Statement",
    description:
      "Get income statement data: revenue, operating profit, net profit, EPS, gross margin, etc. " +
      "period format YYYYMMDD (e.g. 20231231 for annual, 20230930 for Q3). " +
      "report_type: 1=合并报表(default), 2=单季合并, 3=调整单季合并, 4=调整合并, 5=调整前合并.",
    parameters: {
      type: "object",
      properties: {
        ts_code: { type: "string", description: "Stock code (required)" },
        period: { type: "string", description: "Report period YYYYMMDD e.g. 20231231" },
        report_type: { type: "string", description: "Report type 1-5, default 1" },
        start_date: { type: "string", description: "Ann date start YYYYMMDD" },
        end_date: { type: "string", description: "Ann date end YYYYMMDD" },
      },
      required: ["ts_code"],
      additionalProperties: false,
    },
    async execute(_id, params) {
      try {
        const p: Record<string, unknown> = { ts_code: params.ts_code };
        if (params.period) p.period = params.period;
        if (params.report_type) p.report_type = params.report_type;
        if (params.start_date) p.start_date = params.start_date;
        if (params.end_date) p.end_date = params.end_date;
        const text = await callTushare(
          token,
          "income",
          p,
          "ts_code,ann_date,end_date,revenue,operate_profit,total_profit,n_income,n_income_attr_p,basic_eps,diluted_eps,report_type",
        );
        return { content: [{ type: "text", text }], details: {} };
      } catch (e) {
        return { content: [{ type: "text", text: `Error: ${e}` }], details: {} };
      }
    },
  });

  // ── Balance Sheet ─────────────────────────────────────────────────────────────
  api.registerTool({
    name: "tushare_balancesheet",
    label: "Tushare Balance Sheet",
    description:
      "Get balance sheet data: total assets, total liabilities, shareholders equity, cash & equivalents, " +
      "inventory, accounts receivable, debt structure. period format YYYYMMDD.",
    parameters: {
      type: "object",
      properties: {
        ts_code: { type: "string", description: "Stock code (required)" },
        period: { type: "string", description: "Report period YYYYMMDD" },
        report_type: { type: "string", description: "Report type 1-5" },
        start_date: { type: "string", description: "Ann date start YYYYMMDD" },
        end_date: { type: "string", description: "Ann date end YYYYMMDD" },
      },
      required: ["ts_code"],
      additionalProperties: false,
    },
    async execute(_id, params) {
      try {
        const p: Record<string, unknown> = { ts_code: params.ts_code };
        if (params.period) p.period = params.period;
        if (params.report_type) p.report_type = params.report_type;
        if (params.start_date) p.start_date = params.start_date;
        if (params.end_date) p.end_date = params.end_date;
        const text = await callTushare(
          token,
          "balancesheet",
          p,
          "ts_code,ann_date,end_date,total_assets,total_liab,total_hldr_eqy_inc_min_int,money_cap,accounts_receiv,inventories,lt_borr,st_borr,report_type",
        );
        return { content: [{ type: "text", text }], details: {} };
      } catch (e) {
        return { content: [{ type: "text", text: `Error: ${e}` }], details: {} };
      }
    },
  });

  // ── Cash Flow Statement ──────────────────────────────────────────────────────
  api.registerTool({
    name: "tushare_cashflow",
    label: "Tushare Cash Flow",
    description:
      "Get cash flow statement: operating/investing/financing cash flows, free cash flow, capex. " +
      "Key fields: n_cashflow_act (operating CF), n_cashflow_inv_act (investing CF), " +
      "n_cash_flows_fnc_act (financing CF), free_cashflow.",
    parameters: {
      type: "object",
      properties: {
        ts_code: { type: "string", description: "Stock code (required)" },
        period: { type: "string", description: "Report period YYYYMMDD" },
        report_type: { type: "string", description: "Report type 1-5" },
        start_date: { type: "string", description: "Ann date start YYYYMMDD" },
        end_date: { type: "string", description: "Ann date end YYYYMMDD" },
      },
      required: ["ts_code"],
      additionalProperties: false,
    },
    async execute(_id, params) {
      try {
        const p: Record<string, unknown> = { ts_code: params.ts_code };
        if (params.period) p.period = params.period;
        if (params.report_type) p.report_type = params.report_type;
        if (params.start_date) p.start_date = params.start_date;
        if (params.end_date) p.end_date = params.end_date;
        const text = await callTushare(
          token,
          "cashflow",
          p,
          "ts_code,ann_date,end_date,n_cashflow_act,n_cashflow_inv_act,n_cash_flows_fnc_act,free_cashflow,c_pay_acq_const_fiolta,report_type",
        );
        return { content: [{ type: "text", text }], details: {} };
      } catch (e) {
        return { content: [{ type: "text", text: `Error: ${e}` }], details: {} };
      }
    },
  });

  // ── Financial Indicators ─────────────────────────────────────────────────────
  api.registerTool({
    name: "tushare_fina_indicator",
    label: "Tushare Financial Indicators",
    description:
      "Get computed financial ratios: ROE, ROA, gross margin, net margin, debt-to-equity, " +
      "current ratio, EPS, BVPS, revenue growth, profit growth. " +
      "Great for fundamental screening and quality assessment.",
    parameters: {
      type: "object",
      properties: {
        ts_code: { type: "string", description: "Stock code (required)" },
        period: { type: "string", description: "Report period YYYYMMDD" },
        start_date: { type: "string", description: "Ann date start YYYYMMDD" },
        end_date: { type: "string", description: "Ann date end YYYYMMDD" },
      },
      required: ["ts_code"],
      additionalProperties: false,
    },
    async execute(_id, params) {
      try {
        const p: Record<string, unknown> = { ts_code: params.ts_code };
        if (params.period) p.period = params.period;
        if (params.start_date) p.start_date = params.start_date;
        if (params.end_date) p.end_date = params.end_date;
        const text = await callTushare(
          token,
          "fina_indicator",
          p,
          "ts_code,ann_date,end_date,roe,roe_dt,roa,gross_profit_margin,netprofit_margin,debt_to_assets,current_ratio,quick_ratio,eps,bps,revenue_yoy,netprofit_yoy,fcff,fcfe",
        );
        return { content: [{ type: "text", text }], details: {} };
      } catch (e) {
        return { content: [{ type: "text", text: `Error: ${e}` }], details: {} };
      }
    },
  });

  // ── Earnings Forecast ────────────────────────────────────────────────────────
  api.registerTool({
    name: "tushare_forecast",
    label: "Tushare Earnings Forecast",
    description:
      "Get earnings forecast/pre-announcement data. Companies announce profit guidance before formal reports. " +
      "type: 预增|预减|扭亏|首亏|续亏|续盈|略增|略减. " +
      "Returns net_profit_min/max forecast ranges and yoy change.",
    parameters: {
      type: "object",
      properties: {
        ts_code: { type: "string", description: "Stock code" },
        ann_date: { type: "string", description: "Announcement date YYYYMMDD" },
        start_date: { type: "string", description: "Ann date start YYYYMMDD" },
        end_date: { type: "string", description: "Ann date end YYYYMMDD" },
        period: { type: "string", description: "Report period YYYYMMDD" },
        type: { type: "string", description: "Forecast type e.g. 预增" },
      },
      additionalProperties: false,
    },
    async execute(_id, params) {
      try {
        const p: Record<string, unknown> = {};
        if (params.ts_code) p.ts_code = params.ts_code;
        if (params.ann_date) p.ann_date = params.ann_date;
        if (params.start_date) p.start_date = params.start_date;
        if (params.end_date) p.end_date = params.end_date;
        if (params.period) p.period = params.period;
        if (params.type) p.type = params.type;
        const text = await callTushare(
          token,
          "forecast",
          p,
          "ts_code,ann_date,end_date,type,net_profit_min,net_profit_max,last_parent_net,first_ann_date,summary",
        );
        return { content: [{ type: "text", text }], details: {} };
      } catch (e) {
        return { content: [{ type: "text", text: `Error: ${e}` }], details: {} };
      }
    },
  });

  // ── Northbound/Southbound Money Flow (沪深港通资金流向) ─────────────────────
  api.registerTool({
    name: "tushare_moneyflow_hsgt",
    label: "Tushare Northbound/Southbound Flow",
    description:
      "Get daily aggregate northbound (沪股通+深股通) and southbound (港股通) capital flows. " +
      "buy_elg_amount=北向买入额, buy_elg_net_amount=北向净买入额. " +
      "Critical indicator for foreign institutional flows into A-shares.",
    parameters: {
      type: "object",
      properties: {
        trade_date: { type: "string", description: "Trading date YYYYMMDD" },
        start_date: { type: "string", description: "Start date YYYYMMDD" },
        end_date: { type: "string", description: "End date YYYYMMDD" },
      },
      additionalProperties: false,
    },
    async execute(_id, params) {
      try {
        const p: Record<string, unknown> = {};
        if (params.trade_date) p.trade_date = params.trade_date;
        if (params.start_date) p.start_date = params.start_date;
        if (params.end_date) p.end_date = params.end_date;
        const text = await callTushare(
          token,
          "moneyflow_hsgt",
          p,
          "trade_date,ggt_ss,ggt_sz,hgt,sgt,north_money,south_money",
        );
        return { content: [{ type: "text", text }], details: {} };
      } catch (e) {
        return { content: [{ type: "text", text: `Error: ${e}` }], details: {} };
      }
    },
  });

  // ── Top 10 Northbound Holdings (沪深港通十大成交股) ────────────────────────
  api.registerTool({
    name: "tushare_hsgt_top10",
    label: "Tushare Northbound Top 10 Stocks",
    description:
      "Get top 10 A-share stocks by northbound (沪深港通) trading volume on a given date. " +
      "market_type: 1=沪股通(Shanghai), 3=深股通(Shenzhen), 2=港股通(Shanghai to HK), 4=港股通(Shenzhen to HK). " +
      "Shows buy/sell amounts and net buy for each stock.",
    parameters: {
      type: "object",
      properties: {
        trade_date: { type: "string", description: "Trading date YYYYMMDD (required)" },
        ts_code: { type: "string", description: "Stock code filter" },
        market_type: { type: "string", description: "1=沪股通 3=深股通 2/4=港股通" },
        start_date: { type: "string", description: "Start date YYYYMMDD" },
        end_date: { type: "string", description: "End date YYYYMMDD" },
      },
      additionalProperties: false,
    },
    async execute(_id, params) {
      try {
        const p: Record<string, unknown> = {};
        if (params.trade_date) p.trade_date = params.trade_date;
        if (params.ts_code) p.ts_code = params.ts_code;
        if (params.market_type) p.market_type = params.market_type;
        if (params.start_date) p.start_date = params.start_date;
        if (params.end_date) p.end_date = params.end_date;
        const text = await callTushare(
          token,
          "hsgt_top10",
          p,
          "trade_date,ts_code,name,close,change,rank,market_type,amount,net_amount,buy,sell",
        );
        return { content: [{ type: "text", text }], details: {} };
      } catch (e) {
        return { content: [{ type: "text", text: `Error: ${e}` }], details: {} };
      }
    },
  });

  // ── Top 10 Shareholders ──────────────────────────────────────────────────────
  api.registerTool({
    name: "tushare_top10_holders",
    label: "Tushare Top 10 Shareholders",
    description:
      "Get top 10 shareholders (前十大股东) for a stock at a reporting period. " +
      "Shows holder name, shares held, shareholding ratio, and holder type. " +
      "Use top10_floatholders for floating shareholders (流通股东).",
    parameters: {
      type: "object",
      properties: {
        ts_code: { type: "string", description: "Stock code (required)" },
        period: { type: "string", description: "Report period YYYYMMDD" },
        ann_date: { type: "string", description: "Announcement date YYYYMMDD" },
        start_date: { type: "string", description: "Start date YYYYMMDD" },
        end_date: { type: "string", description: "End date YYYYMMDD" },
        holder_type: { type: "string", description: "Holder type filter" },
      },
      required: ["ts_code"],
      additionalProperties: false,
    },
    async execute(_id, params) {
      try {
        const p: Record<string, unknown> = { ts_code: params.ts_code };
        if (params.period) p.period = params.period;
        if (params.ann_date) p.ann_date = params.ann_date;
        if (params.start_date) p.start_date = params.start_date;
        if (params.end_date) p.end_date = params.end_date;
        if (params.holder_type) p.holder_type = params.holder_type;
        const text = await callTushare(
          token,
          "top10_holders",
          p,
          "ts_code,ann_date,end_date,holder_name,hold_amount,hold_ratio,hold_float_ratio,hold_change,holder_type",
        );
        return { content: [{ type: "text", text }], details: {} };
      } catch (e) {
        return { content: [{ type: "text", text: `Error: ${e}` }], details: {} };
      }
    },
  });

  // ── Index Daily ──────────────────────────────────────────────────────────────
  api.registerTool({
    name: "tushare_index_daily",
    label: "Tushare Index Daily",
    description:
      "Get daily data for major indices. Common ts_code: 000001.SH (上证综指), " +
      "399001.SZ (深证成指), 399006.SZ (创业板指), 000300.SH (沪深300), " +
      "000905.SH (中证500), 000852.SH (中证1000), HSI.HI (恒生指数), HSCEI.HI (国企指数).",
    parameters: {
      type: "object",
      properties: {
        ts_code: { type: "string", description: "Index code e.g. 000001.SH" },
        trade_date: { type: "string", description: "Trading date YYYYMMDD" },
        start_date: { type: "string", description: "Start date YYYYMMDD" },
        end_date: { type: "string", description: "End date YYYYMMDD" },
      },
      additionalProperties: false,
    },
    async execute(_id, params) {
      try {
        const p: Record<string, unknown> = {};
        if (params.ts_code) p.ts_code = params.ts_code;
        if (params.trade_date) p.trade_date = params.trade_date;
        if (params.start_date) p.start_date = params.start_date;
        if (params.end_date) p.end_date = params.end_date;
        const text = await callTushare(
          token,
          "index_daily",
          p,
          "ts_code,trade_date,open,high,low,close,change,pct_chg,vol,amount",
        );
        return { content: [{ type: "text", text }], details: {} };
      } catch (e) {
        return { content: [{ type: "text", text: `Error: ${e}` }], details: {} };
      }
    },
  });

  // ── Trade Calendar ───────────────────────────────────────────────────────────
  api.registerTool({
    name: "tushare_trade_cal",
    label: "Tushare Trade Calendar",
    description:
      "Get A-share trading calendar. is_open=1 for trading days, 0 for non-trading days. " +
      "Useful to verify if a date is a valid trading day.",
    parameters: {
      type: "object",
      properties: {
        exchange: { type: "string", description: "Exchange: SSE | SZSE (default SSE)" },
        start_date: { type: "string", description: "Start date YYYYMMDD" },
        end_date: { type: "string", description: "End date YYYYMMDD" },
        is_open: { type: "string", description: "1=trading day, 0=non-trading" },
      },
      additionalProperties: false,
    },
    async execute(_id, params) {
      try {
        const p: Record<string, unknown> = {};
        if (params.exchange) p.exchange = params.exchange;
        if (params.start_date) p.start_date = params.start_date;
        if (params.end_date) p.end_date = params.end_date;
        if (params.is_open) p.is_open = params.is_open;
        const text = await callTushare(token, "trade_cal", p, "exchange,cal_date,is_open,pretrade_date");
        return { content: [{ type: "text", text }], details: {} };
      } catch (e) {
        return { content: [{ type: "text", text: `Error: ${e}` }], details: {} };
      }
    },
  });

  // ── Dividend ─────────────────────────────────────────────────────────────────
  api.registerTool({
    name: "tushare_dividend",
    label: "Tushare Dividend History",
    description:
      "Get dividend and rights issue history for a stock. " +
      "Returns cash_div (每股股利), stk_div (每股送股), record_date, ex_date, pay_date.",
    parameters: {
      type: "object",
      properties: {
        ts_code: { type: "string", description: "Stock code (required)" },
        ann_date: { type: "string", description: "Announcement date YYYYMMDD" },
        record_date: { type: "string", description: "Record date YYYYMMDD" },
        ex_date: { type: "string", description: "Ex-dividend date YYYYMMDD" },
        imp_ann_date: { type: "string", description: "Implementation announcement date" },
      },
      required: ["ts_code"],
      additionalProperties: false,
    },
    async execute(_id, params) {
      try {
        const p: Record<string, unknown> = { ts_code: params.ts_code };
        if (params.ann_date) p.ann_date = params.ann_date;
        if (params.record_date) p.record_date = params.record_date;
        if (params.ex_date) p.ex_date = params.ex_date;
        if (params.imp_ann_date) p.imp_ann_date = params.imp_ann_date;
        const text = await callTushare(
          token,
          "dividend",
          p,
          "ts_code,end_date,ann_date,div_proc,stk_div,stk_bo_rate,stk_co_rate,cash_div,cash_div_tax,record_date,ex_date,pay_date",
        );
        return { content: [{ type: "text", text }], details: {} };
      } catch (e) {
        return { content: [{ type: "text", text: `Error: ${e}` }], details: {} };
      }
    },
  });

  api.logger.info("Tushare plugin registered 14 financial data tools.");
}
