source "$SCRIPTS_DIR/variables/common.sh"
source "$SCRIPTS_DIR/deploy/before_task.sh"

cp "$SCRIPTS_DIR/deploy/tasks/reset_pipeline.py" "$workdir/backends/"
task_path="$workdir/backends/reset_pipeline.py"
python $task_path
source "$SCRIPTS_DIR/deploy/after_task.sh"
rm -f $task_path