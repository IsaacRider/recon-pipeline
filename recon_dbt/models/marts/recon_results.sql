-- THE CENTERPIECE: reconcile the two payment sources.
--
-- A FULL OUTER JOIN keeps transactions that exist in EITHER source, so we can catch
-- both "in internal but never settled" and "settled but no internal record". A CASE
-- expression then classifies each transaction, mirroring the Python reconcile() logic.

with internal as (
    select * from {{ ref('stg_internal_transactions') }}
),

processor as (
    select * from {{ ref('stg_processor_settlements') }}
),

joined as (
    select
        coalesce(i.transaction_id, p.transaction_id) as transaction_id,
        i.agency,
        i.internal_amount,
        p.processor_amount,
        round(coalesce(i.internal_amount, 0)
              - coalesce(p.processor_amount, 0), 2) as amount_difference
    from internal i
    full outer join processor p
        on i.transaction_id = p.transaction_id
),

classified as (
    select
        *,
        case
            when internal_amount is not null and processor_amount is null
                then 'MISSING_IN_PROCESSOR'
            when internal_amount is null and processor_amount is not null
                then 'UNEXPECTED_IN_PROCESSOR'
            when abs(coalesce(amount_difference, 0)) <= 0.005
                then 'MATCHED'
            else 'AMOUNT_MISMATCH'
        end as recon_status
    from joined
)

select * from classified
