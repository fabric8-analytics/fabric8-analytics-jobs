directories="f8a_jobs tests"

# checks for the whole directories
for directory in $directories
do
    grep -r -n "TODO: " $directory
done
