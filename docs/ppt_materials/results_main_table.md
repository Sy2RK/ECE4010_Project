# Main Results Table

Source runs after post-practice replanning and compact adaptive guidance: `outputs/sample_api_run_29`, `outputs/sample_api_run_30`.

| mode | avg_pretest_score | avg_posttest_score | avg_delta | sample_count | std_delta | grammar_delta | reading_delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| no_guidance | 0.719 | 0.697 | -0.022 | 12 | 0.043 | -0.027 | -0.017 |
| generic_guidance | 0.719 | 0.821 | 0.102 | 12 | 0.119 | 0.020 | 0.184 |
| adaptive_guidance | 0.719 | 0.854 | 0.135 | 12 | 0.147 | 0.035 | 0.235 |

PPT-safe takeaway: after post-practice replanning, adaptive guidance is strongest in the latest validation runs, especially on Reading QA. Keep the claim scoped to this prototype and small dataset.
