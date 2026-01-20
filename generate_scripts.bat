@echo off

REM Easy Partitions
echo Creating scripts for Easy Partitions (Male/Female)...

(
echo python edit_main.py --model 9b --difficulty easy --gender female --partition partition_0
) > bash_scripts/easy/run_easy_female_p0.bat
(
echo python edit_main.py --model 9b --difficulty easy --gender female --partition partition_1
) > bash_scripts/easy/run_easy_female_p1.bat
(
echo python edit_main.py --model 9b --difficulty easy --gender female --partition partition_2
) > bash_scripts/easy/run_easy_female_p2.bat
(
echo python edit_main.py --model 9b --difficulty easy --gender female --partition partition_3
) > bash_scripts/easy/run_easy_female_p3.bat

(
echo python edit_main.py --model 9b --difficulty easy --gender male --partition partition_0
) > bash_scripts/easy/run_easy_male_p0.bat
(
echo python edit_main.py --model 9b --difficulty easy --gender male --partition partition_1
) > bash_scripts/easy/run_easy_male_p1.bat
(
echo python edit_main.py --model 9b --difficulty easy --gender male --partition partition_2
) > bash_scripts/easy/run_easy_male_p2.bat
(
echo python edit_main.py --model 9b --difficulty easy --gender male --partition partition_3
) > bash_scripts/easy/run_easy_male_p3.bat


REM Medium Partitions
echo Creating scripts for Medium Partitions (Male/Female)...

(
echo python edit_main.py --model 9b --difficulty medium --gender female --partition partition_0
) > bash_scripts/medium/run_medium_female_p0.bat
(
echo python edit_main.py --model 9b --difficulty medium --gender female --partition partition_1
) > bash_scripts/medium/run_medium_female_p1.bat
(
echo python edit_main.py --model 9b --difficulty medium --gender female --partition partition_2
) > bash_scripts/medium/run_medium_female_p2.bat
(
echo python edit_main.py --model 9b --difficulty medium --gender female --partition partition_3
) > bash_scripts/medium/run_medium_female_p3.bat

(
echo python edit_main.py --model 9b --difficulty medium --gender male --partition partition_0
) > bash_scripts/medium/run_medium_male_p0.bat
(
echo python edit_main.py --model 9b --difficulty medium --gender male --partition partition_1
) > bash_scripts/medium/run_medium_male_p1.bat
(
echo python edit_main.py --model 9b --difficulty medium --gender male --partition partition_2
) > bash_scripts/medium/run_medium_male_p2.bat
(
echo python edit_main.py --model 9b --difficulty medium --gender male --partition partition_3
) > bash_scripts/medium/run_medium_male_p3.bat


REM Hard Partitions
echo Creating scripts for Hard Partitions (Male/Female)...

(
echo python edit_main.py --model 9b --difficulty hard --gender female --partition partition_0
) > bash_scripts/hard/run_hard_female_p0.bat
(
echo python edit_main.py --model 9b --difficulty hard --gender female --partition partition_1
) > bash_scripts/hard/run_hard_female_p1.bat
(
echo python edit_main.py --model 9b --difficulty hard --gender female --partition partition_2
) > bash_scripts/hard/run_hard_female_p2.bat
(
echo python edit_main.py --model 9b --difficulty hard --gender female --partition partition_3
) > bash_scripts/hard/run_hard_female_p3.bat

(
echo python edit_main.py --model 9b --difficulty hard --gender male --partition partition_0
) > bash_scripts/hard/run_hard_male_p0.bat
(
echo python edit_main.py --model 9b --difficulty hard --gender male --partition partition_1
) > bash_scripts/hard/run_hard_male_p1.bat
(
echo python edit_main.py --model 9b --difficulty hard --gender male --partition partition_2
) > bash_scripts/hard/run_hard_male_p2.bat
(
echo python edit_main.py --model 9b --difficulty hard --gender male --partition partition_3
) > bash_scripts/hard/run_hard_male_p3.bat


echo Done! Detailed gender/partition scripts generated in bash_scripts/ folder.
