# memory Management debugging
# incorrect logs

complexity_level: "simple"

title: "Fix issues with the memory management system after reviewing logs"

task: |
  The memory manager is a sophisticated embeded mememory manager for STM32 and LINUX_PLATFORM version of the Fleet Connect product.
  We are working on the LINUX_PLATFORM version.
  Review all source in the directory ~/iMatrix/iMatrix_Client/cs_ctrl and create a document ~/iMatrix/docs/mm_details.md to use as a reference as we debug and fix these issue.
  As yu review logs find the first sign of corrupuption stop furhter examintaion.
  Must fix first issue.
  Run more users tests and review logs in cycle until there are no more issue
  The logs are long use and agent to read them in small sections
  Read intialy log file ~/iMatrix/iMatrix_Client/logs/mm1.txt

branch: "bugfix/memory_manager_1"

notes:
  - "Happens when processing normal sampling data"

files_to_modify:
  - "iMatrix/cs_ctrl"

# Optional: Override default branch if needed
# prompt_name will be auto-generated from title as: fix_memory_leak_in_can_processing


