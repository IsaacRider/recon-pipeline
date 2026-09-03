-- Clean + type-cast the raw processor settlement records.

with source as (
    select * from {{ source('raw', 'raw_processor_settlements') }}
),

cleaned as (
    select
        settlement_id,
        transaction_id,
        cast(settled_amount as double)  as processor_amount,
        cast(settled_at as timestamp)   as settled_at
    from source
    where transaction_id is not null
)

select * from cleaned
