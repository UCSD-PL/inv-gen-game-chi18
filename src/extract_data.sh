#!/bin/sh
# Extract data from the database for graphing

set -e

db="$1"

mkdir -p data

# Solved levels for workers at or below each experience level
#
# Some workers responded with different answers for experience level:
# =Math
#   select distinct worker,
#     count(distinct json_extract(payload, "$.math_experience"))
#   from surveydata group by worker;
# =Programming
#   select distinct worker,
#     count(distinct json_extract(payload, "$.prog_experience"))
#   from surveydata group by worker;
for exp in math prog; do
  # We may want to include more config parameters here
  sqlite3 -header -separator ' ' "$db" "
    select lvl,
      sum(
        json_extract(payload, \"$.workers[0]\") in (
          select distinct worker from surveydata
          where cast(json_extract(payload, \"$.${exp}_experience\")
            as integer) <= 1
        )
      ) as exp_1,
      sum(
        json_extract(payload, \"$.workers[0]\") in (
          select distinct worker from surveydata
          where cast(json_extract(payload, \"$.${exp}_experience\")
            as integer) <= 2
        )
      ) as exp_2,
      sum(
        json_extract(payload, \"$.workers[0]\") in (
          select distinct worker from surveydata
          where cast(json_extract(payload, \"$.${exp}_experience\")
            as integer) <= 3
        )
      ) as exp_3,
      sum(
        json_extract(payload, \"$.workers[0]\") in (
          select distinct worker from surveydata
          where cast(json_extract(payload, \"$.${exp}_experience\")
            as integer) <= 4
        )
      ) as exp_4,
      sum(
        json_extract(payload, \"$.workers[0]\") in (
          select distinct worker from surveydata
          where cast(json_extract(payload, \"$.${exp}_experience\")
            as integer) <= 5
        )
      ) as exp_5
    from verifydata
    where json_extract(config, \"$.mode\") = \"individual\"
      and provedflag = 1
    group by lvl
  " >"data/lvl_$exp.dat"
  # Combined versions
  sqlite3 -header -separator ' ' "$db" "
    select exp, count(t2.lvl) as nsolved, json_group_array(t2.lvl) as lvls
    from (
      select 1 as exp
      union select 2
      union select 3
      union select 4
      union select 5
    ) as t1
    left outer join (
      select lvl, min(cast(substr(json_extract(config, \"$.tag\"), -1)
      as integer)) as min_exp
        from verifydata
      where json_extract(config, \"$.mode\") = \"combined\"
        and json_extract(config, \"$.tag\") like \"$exp-exp-le-%\"
        and provedflag = 1
      group by lvl
    ) as t2
      on t1.exp >= t2.min_exp
    group by exp
  " >"data/lvl_${exp}_combined.dat"
done
