## Debug mode (on for this run)
Before and after every Agent call print `▶ <phase> | <role> | <model> | <effort> | <why>` and
`◀ <phase> | <result> | <changed files> | <checks>`. End the report with the receipt from
`python3 -I "${SKILL}/scripts/tokens.py" --session <session id> --since <start> --phases`.
