# Python Mobility Simulator (PyMoSIm)

Description
-----------
This is a python mobility simulator. It aims to provide an easy-to-use 
coding environment for vehicular network simulation.

How to sync with this project
----------------------------------

##### Configure your git environment
Use the following command to configure your git environment with your university email:
```bash
git config --global user.email "ab0012@surrey.ac.uk"
```
##### Clone this project
Clone the project to your local repository (i.e. your local disk). The command will create a folder named 'pymosim'. Use the last command to check the status.
```bash
git clone https://gitlab.eps.surrey.ac.uk/cf0014/pymosim.git
cd pymosim
git status
```
##### Pull updates to your local repository
Pull the 'master' branch to your local repository.
```bash
git pull origin master
```
The 'origin' should have already set properly when cloning the project. You can check the 'origin' URL by using the first command in the following, or manually set it by using the second command.
```bash
git remove -v
git remote add origin https://gitlab.eps.surrey.ac.uk/cf0014/pymosim.git
```
You may need to pull the changes from time to time to use the newer features added to the remote repository.

##### Push changes to the remote repository
Note that you should not push any code back to this repository unless you
are asked to contribute to the package development. To push changes to the 'master' branch, do the following:
```bash
git add 'some_files'
    # note: add only source code, do not add other types of files (e.g. *.pyc)
git commit -m 'short comment on changes made'
git push origin master
```

Recommended Python Version and Important Dependencies
-------------------------------------------
- Python 3.7.10
- wxPython 4.0.4

How to build a simulation
-------------------------
You can find several examples in the main folder showing how to build a 
mobility simulation. You should notice that the examples use other packages
to create a scenario, put some nodes in the scenarios, and describe the 
communication and mobility models for the created nodes.

The packages that the simulator provides includes `sim`, `node` and `comm`. 
You should not touch the files inside those folders. Instead, you should 
just use them. To learn how to use them, please see the `html` folder 
for the documentation.

You should focus on developing your scenario and testing your algorithm
using the simulator. You should not modify the simulator packages. If you 
need any feature current unavailable in the packages, please let me know.
Please also report any bug to me.


