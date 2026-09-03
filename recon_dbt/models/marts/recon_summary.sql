-- Aggregated view for reporting / BI: counts and dollar exposure per status,
-- broken down by agency. This is what feeds the dashboard.

with results as (
    select * from {{ ref('recon_results') }}
)

select
    coalesce(agency, 'UNKNOWN')                as agency,
    recon_status,
    count(*)                                   as txn_count,
    round(sum(coalesce(internal_amount, 0)), 2)  as total_internal_amount,
    round(sum(coalesce(processor_amount, 0)), 2) as total_processor_amount,
    round(sum(coalesce(amount_difference, 0)), 2) as total_difference
from results
group by 1, 2
order by 1, 2
