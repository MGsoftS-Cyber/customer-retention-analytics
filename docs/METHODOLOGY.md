# Analytical methodology

## Input and observation

One row per aggregate order, exact header customer_id,order_id,order_date,amount,status. IDs use letters/digits/underscores/hyphens up to 80 characters. Dates are ISO calendar days, no future orders. Maximum 10000 orders, 2000000 CSV characters and 1826 days of coverage. Amounts are decimal text (up to 1e9, at most two decimals); normalized integer cents eliminate binary-float revenue errors. USD, EUR, GBP and DZD use two decimals here.

Coverage end is user-declared complete observation, can include days with no orders, must include every row and cannot be future. Analysis date lies between observed start and coverage end. Source-system timezone and identity merging must be consistent upstream. Later orders and non-completed statuses are excluded before all customer calculations. Historical analyses assume imported final statuses; the dataset has no refund/status event history for point-in-time reconstruction.

## Population and metrics

Purchasing customers = distinct IDs among included completed orders. Completed order count = unique imported order records (duplicates reject). Revenue = sum integer cents. Average order value = revenue/order count, rounded half-up to nearest minor unit. Repeat buyer has at least two completed orders; repeat rate = repeat buyers/purchasing customers. It has no fixed follow-up window and is affected by new-customer maturity. Empty populations return null rates and empty customer/cohort lists.

## Cohorts

Acquisition cohort is calendar month of first observed completed purchase. Cohort size is the number of purchasing customers assigned there. M0 is 100% acquisition baseline. For age k>=1, exact-month retention = distinct cohort customers with at least one completed purchase in that target month / original cohort size. Multiple orders count a customer once. A buyer may return after a gap: rates need not decrease monotonically. This is not consecutive survival or subscription cancellation.

Follow-up months strictly earlier than analysis-date month are closed and observable. Current/future months are null, even on the last day of the current month (conservative closure). Closed months with no returns are 0%. The current acquisition cohort M0 remains baseline, not a mature outcome. Monthly activity marks the current month as partial. Incomplete prehistory changes first-observed acquisition; missing later facts depress retention. Declared coverage is not independently verified.

## RFM

Recency = as_of - latest completed purchase, days. Frequency = completed order count in observed history. Monetary = total completed-order cents. For each field and unique value, midrank percentile = (count strictly less + count less-or-equal)/(2*N). Score = ceil(5*percentile), clipped 1..5. Recency score is inverted (6-score); frequency and monetary retain ascending scores. Ties get identical scores; all-equal gives 3. Scores are relative to the analyzed population and can change with a new dataset/date.

## Segment priority

1. Long inactive: recency > 2*inactivity_days.
2. At risk: recency > inactivity_days.
3. Champions: R,F,M each at least 4.
4. New buyers: frequency=1 and recency<=30 days.
5. Loyal buyers: F>=4.
6. Developing buyers: remaining population.

These rules are application choices, not a universal RFM standard or calibrated churn labels. Inactive summary uses recency strictly greater than threshold, including both At risk and Long inactive. No automated customer contact or campaign is sent.

## Money and refunds

Cancelled and fully refunded orders are entirely excluded from count, acquisition, activity and revenue. Partial refunds are unsupported; upstream can supply a documented net completed amount, but the order still counts as a purchase. Zero-value completed orders count; choose upstream business rules intentionally. No currency conversion, tax/accounting reconciliation, future CLV or churn prediction.

Background references (this release uses its own explicit rules): Shopify https://www.shopify.com/blog/rfm-analysis ; Google Analytics https://support.google.com/analytics/answer/9670133?hl=en .
