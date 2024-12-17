# RESA: REpair for StAbility

Resa is a an automated planning tool that starts from one or more plans and computes a plan that is the most stable plan w.r.t. the given input. 

Resa is written in python and uses the Unified Planning (UP) for manipulating planning problems and the grounder of FastDownward. In what follows, the necessary steps to make it run.

### Step 1: Install Python
Ensure you have Python 3.8 or later installed. You can download it from the official Python website if needed.

###  Step 2: Set Up a Virtual Environment (Optional)
To avoid conflicts with other Python packages, it's a good practice to use a virtual environment. Type the next commands:

python -m venv up_env
source up_env/bin/activate

### Step 3: Install the Unified Planning
Make sure that you have the last pip version installed and then install the library using pip:

python3 -m pip install --upgrade pip   
pip install unified-planning==0.4.2.382.dev1

### Step 4: Download the FastDownward Grounder

git clone https://github.com/LBonassi95/downward.git

(working commit f02bd159d8af154e73f22a68cd0fd17c2a523f0f)

### Step 4: Install click

pip install click

You are now ready to run Resa. The command line for Resa, S-Resa and L-Resa is as follows:

<RESA-VERSION>.sh <DOMAIN> <PROBLEM> <DIR-DEST> <PLAN>

where <RESA-VERSION> is the version of Resa you intend to run, <DOMAIN> is the file encoding the PDDL domains, <PROBLEM> is the file encoding the PDDL problem, <DIR-DEST> is the directory where saving the compiled domain and problem, <PLAN> is the file encoding the input plan.

For instance, type:

cd Resa
./resa.sh ../Example/caldera.pddl ../Example/pfile01.pddl . ../Example/pfile01.soln

The output of resa is the compiled domain and problem files, that are created in the directory where the script is launched. 

The command line for M-Resa is as follows:

./m-resa.sh <DOMAIN> <PROBLEM> <DIR-DEST> <PLAN-DIR>

where <PLAN-DIR> is the directory containing a set of solutions.

For instance, type:

cd M-Resa
./m-resa.sh  ../Example/caldera.pddl ../Example/pfile01.pddl . ../Example/2SOL

or 

./m-resa.sh  ../Example/caldera.pddl ../Example/pfile01.pddl . ../Example/5SOL

to compute a compiled problem for the multi-repair planning problem with 2 and 5 input plans, respectively.


