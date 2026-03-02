Open Terminal and run:
git clone https://github.com/INTEGRIIT/AutonomousSync.git
cd AutonomousSync

This downloads the full project to your computer.

Step 2 – Switch to Your Assigned Branch
You MUST switch to your branch before editing.

git fetch --all
git checkout feature/battery-protection-engine

git fetch --all
git checkout feature/backup-service

git fetch --all
git checkout feature/android-integration

Step 3 – Confirm You Are On The Correct Branch
git branch

Step 5 – Save and Push Your Work
git add .
git commit -m "Implement feature logic"

If Git says the branch has no upstream:
git push -u origin feature/branch-name
After:
git push


If Git complains branch doesn’t exist locally:
git checkout -b feature/battery-protection-engine origin/feature/battery-protection-engine