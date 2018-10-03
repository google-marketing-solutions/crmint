source "$SCRIPTS_DIR/variables/common.sh"
source "$SCRIPTS_DIR/deploy/before_task.sh"

cp "$SCRIPTS_DIR/deploy/tasks/seeds.py" "$workdir/backends/"
task_path="$workdir/backends/seeds.py"
python $task_path
source "$SCRIPTS_DIR/deploy/after_task.sh"
rm -f $task_path