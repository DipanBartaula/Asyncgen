@echo off

REM Easy Partitions (Partition 0 - 3)
echo Creating scripts for Easy Partitions...

(
echo python edit_main.py --model 9b --difficulty easy --partition partition_0
) > bash_scripts/easy/run_easy_p0.bat

(
echo python edit_main.py --model 9b --difficulty easy --partition partition_1
) > bash_scripts/easy/run_easy_p1.bat

(
echo python edit_main.py --model 9b --difficulty easy --partition partition_2
) > bash_scripts/easy/run_easy_p2.bat

(
echo python edit_main.py --model 9b --difficulty easy --partition partition_3
) > bash_scripts/easy/run_easy_p3.bat

REM Medium Partitions (Partition 0 - 3)
echo Creating scripts for Medium Partitions...

(
echo python edit_main.py --model 9b --difficulty medium --partition partition_0
) > bash_scripts/medium/run_medium_p0.bat

(
echo python edit_main.py --model 9b --difficulty medium --partition partition_1
) > bash_scripts/medium/run_medium_p1.bat

(
echo python edit_main.py --model 9b --difficulty medium --partition partition_2
) > bash_scripts/medium/run_medium_p2.bat

(
echo python edit_main.py --model 9b --difficulty medium --partition partition_3
) > bash_scripts/medium/run_medium_p3.bat

REM Hard Partitions (Partition 0 - 3)
echo Creating scripts for Hard Partitions...

(
echo python edit_main.py --model 9b --difficulty hard --partition partition_0
) > bash_scripts/hard/run_hard_p0.bat

(
echo python edit_main.py --model 9b --difficulty hard --partition partition_1
) > bash_scripts/hard/run_hard_p1.bat

(
echo python edit_main.py --model 9b --difficulty hard --partition partition_2
) > bash_scripts/hard/run_hard_p2.bat

(
echo python edit_main.py --model 9b --difficulty hard --partition partition_3
) > bash_scripts/hard/run_hard_p3.bat

echo Done! Scripts generated in bash_scripts/ folder.
