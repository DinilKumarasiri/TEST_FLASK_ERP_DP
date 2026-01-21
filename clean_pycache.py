import os
import shutil

def remove_pycache(root_dir):
    removed_dirs = 0

    for root, dirs, files in os.walk(root_dir):
        for dir_name in dirs:
            if dir_name == "__pycache__":
                full_path = os.path.join(root, dir_name)
                try:
                    shutil.rmtree(full_path)
                    print(f"Deleted: {full_path}")
                    removed_dirs += 1
                except Exception as e:
                    print(f"Failed to delete {full_path}: {e}")

    print(f"\n✅ Cleanup complete. Removed {removed_dirs} __pycache__ folders.")

if __name__ == "__main__":
    project_root = os.getcwd()  # run from project root
    print(f"🧹 Cleaning __pycache__ from: {project_root}\n")
    remove_pycache(project_root)
