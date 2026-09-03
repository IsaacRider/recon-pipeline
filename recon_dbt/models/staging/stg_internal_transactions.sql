-- Clean + type-cast the raw internal transaction records.
-- Staging models do light cleanup only: rename, cast, dedupe. No business logic.

with source as (
    select * from {{ source('raw', 'raw_internal_transactions') }}
),

cleaned as (
    select
        transaction_id,
        agency,
        cast(amount as double)      as internal_amount,
        cast(created_at as timestamp) as created_at
    from source
    where transaction_id is not null
)

select * from cleaned
