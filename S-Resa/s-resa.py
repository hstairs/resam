import os, sys
sys.path.append(os.path.dirname(sys.path[0]))
import time
import click
import unified_planning
from unified_planning.io import PDDLReader, PDDLWriter
from unified_planning.engines.mixins.compiler import CompilationKind
from unified_planning.model import Action
from unified_planning.model.metrics import MinimizeActionCosts
from unified_planning.shortcuts import *
unified_planning.shortcuts.get_env().credits_stream = None

from downward.FDgrounder import ground
from downward.FDgrounder import pddl


SEPARATOR = '_'

def create_p_predicate(action_name, index):
    return unified_planning.model.Fluent("p_{}_{}".format(action_name,str(index)))

def create_not_p_predicate(action_name, index):
    return unified_planning.model.Fluent("p_{}_{}".format(action_name,str(index)))

def B(act, index, plan):
    counter = 0
    for i in range(0,index):
        if plan[i] is not None:
            if act == plan[i].name:
                counter +=1
    return counter

def M(act,  plan):
    counter = 0
    for i in range(0,len(plan)):
        if plan[i] is not None:
            if act == plan[i].name:
                counter +=1
    return counter

def create_done(index):
    return unified_planning.model.Fluent("done_{}".format(str(index)))


def compile_ground_problem(problem, plan):
    
    new_problem = unified_planning.model.Problem('repaired-ground')

    F = problem.fluents

    if len(problem.goals[0].args) != 0:
        G = list(problem.goals[0].args)
    else:
        G = problem.goals

    for g in G:
        new_problem.add_goal(g)
       


    I = problem.explicit_initial_values
    p = plan
    
    A = problem.actions
    
    done_atoms = [unified_planning.model.Fluent('done_{}'.format(i), BoolType()) for i in range(0,len(p))]
    w = unified_planning.model.Fluent('w', BoolType())

    costs : Dict[Action, Int]  = {}

    f_set = set()
    f_set = f_set.union(done_atoms)
    f_set.add(w)


    #A_0
    A0 = list()
    for i in range(0,len(p)):
        a = p[i]
        if a is not None:
            name = a.name
            new_a = a.clone()
            new_a.name = name+"_"+str(i)

            new_a.add_precondition(w)
            new_a.add_precondition(create_p_predicate(name,B(name,i,p))) #da testare con altri problemi

            f_set.add(create_p_predicate(name,B(name,i,p)))
            f_set.add(create_p_predicate(name,B(name,i,p)+1))

            new_a.add_effect(create_p_predicate(name,B(name,i,p)+1), True)
            new_a.add_effect(create_not_p_predicate(name,B(name,i,p)), False)
            new_a.add_effect(create_done(i), True)

            costs[new_a] = Int(0)
            A0.append(new_a)
            
    #A1
    A1 = list()
    for a in A:
        if a not in p:
            name = a.name
            new_a = a.clone()
            new_a.name = name

            new_a.add_precondition(w)
            
            costs[new_a] = Int(1)
            A1.append(new_a)
    
    
    #A2
    A2 = list()
    for a in set(p):
        if a is not None:
            I[create_p_predicate(a.name,0)] = True

            name = a.name
            new_a = a.clone()
            new_a.name = name

            new_a.add_precondition(w)

            # COMMENTARE PER LA VERSIONE SENZA A2
            #new_a.add_precondition(self._create_p_predicate(name,self._M(name,p)))

            costs[new_a] = Int(1)
            A2.append(new_a)
    
    
    #A3
    A3 = list()
    Gprime = []
    for i in range(0,len(p)):
        name = a.name
        new_a = unified_planning.model.InstantaneousAction("a_done_{}".format(i))
        new_a.add_precondition(Not(w))
        new_a.add_precondition(Not(create_done(i)))
        new_a.add_effect(create_done(i), True)

        costs[new_a] = Int(1)
        A3.append(new_a)

        Gprime.append(create_done(i))

    # switch
    switch = unified_planning.model.InstantaneousAction("switch")
    switch.add_precondition(w)
    switch.add_effect(w, False)

    costs[switch] = Int(0)
    A3.append(switch)
    
    #Fprime
    F+=list(f_set)
    for i in range(0, len(F)):
        new_problem.add_fluent(F[i], default_initial_value=False)


    #Aprime
    new_problem.add_actions(A0+A1+A2+A3)

    #Iprime
    I[w] = True
    Ikeys = list(I)
    for i in range(0, len(Ikeys)):
        new_problem.set_initial_value(Ikeys[i], I[Ikeys[i]])
    
    
    #Gprime
    for g in Gprime:
        new_problem.add_goal(g)


    #Metric
    metric = MinimizeActionCosts(costs, 0)
    new_problem.add_quality_metric(metric)

    return new_problem

def read_in_plan(problem, filename):
    actions = problem.actions
    plan = list()
    with open(filename) as f:
        for a in  f.readlines():     
            if ";" not in a:            
                a = a.replace("(","").replace(")","").replace(" ","_").strip()
                found = False
                for act in actions:
                    if str(act.name).__eq__(str(a)):
                        plan.append(act)
                        found = True
                if found == False:
                    plan.append(None)
                    print('action {} cannot be found'.format(a))
    
    return plan    
    
def atom_str(atom):
    if len(atom.args) == 0:
        return "%s" % atom.predicate
    else:
        return "%s%s%s" % (atom.predicate, SEPARATOR, SEPARATOR.join(map(str, atom.args)))


def convert_formula(formula):
    if isinstance(formula, pddl.Atom):
        return unified_planning.model.Fluent(atom_str(formula), BoolType())#false
    elif isinstance(formula, pddl.NegatedAtom):
        return Not(unified_planning.model.Fluent(atom_str(formula), BoolType()))#true
    elif isinstance(formula, pddl.Disjunction):
        return Or([convert_formula(part) for part in formula.parts])
    elif isinstance(formula, pddl.Conjunction):
        return And([convert_formula(part) for part in formula.parts])
    elif isinstance(formula, pddl.Truth):
        return TRUE()
    elif isinstance(formula, pddl.Falsity):
        return FALSE()



def convert_ds_up(F, A, I, G):
    F_new = []
    I_new = []
    A_new = []

    ground_problem = unified_planning.model.Problem('ground')
    
    print("=> Converting F...")
    for atom in F:
        F_new.append(convert_formula(atom))
    print("==> Converting I...")
    for atom in I:
        I_new.append(convert_formula(atom))

    print("===>Converting G...")
    G_new = convert_formula(G)
    
    print("====> Converting A...")
    for action in A:
        #print("Converting action: ", action.name)
        preconditions = [convert_formula(pre) for pre in action.precondition]

        new_a = unified_planning.model.InstantaneousAction(action.name.replace(' ', SEPARATOR).replace('(', '').replace(')',''))
        for pre in preconditions:
            new_a.add_precondition(pre)
        
        for cond, eff in action.add_effects:
            if not cond:
                new_a.add_effect(convert_formula(eff), True)
            else:
                new_cond = [convert_formula(lit) for lit in cond]
                new_a.add_effect(convert_formula(eff), True, And(new_cond))
                 
            
            
        for cond, eff in action.del_effects:
            if not cond:
                new_a.add_effect(convert_formula(eff), False)
            else:
                new_cond = [convert_formula(lit) for lit in cond]
                new_a.add_effect(convert_formula(eff), False, And(new_cond))

        A_new.append(new_a)
        #ground_problem.add_action(new_a)

    #F
    print("=====> Inserting F in problem...")
    for i in range(0, len(F_new)):
        ground_problem.add_fluent(F_new[i], default_initial_value=False)

    #A
    print("======> Inserting A in problem...")
    ground_problem.add_actions(A_new)

    #I
    print("=======> Inserting I in problem...")
    for i in range(0, len(I_new)):
        ground_problem.set_initial_value(I_new[i], True)
    
    #G
    print("========> Inserting G in problem...")
    ground_problem.add_goal(G_new)
    
    # Da aggiungere al problema
    return ground_problem




@click.command()
@click.argument('domain')
@click.argument('problem')
@click.argument('output')
@click.argument('planname')
def main(domain, problem, output, planname):

    print("Start")
    start_time = time.time()
    print("Grounding problem...")
    F, A, I, G, _ = ground(domain, problem)
    
    print("Converting...")	
    ground_problem = convert_ds_up(F, A, I, G)

    print("Reading plan...")
    plan = read_in_plan(ground_problem, planname)
    
    print("Starting RESA")
    compiled_problem = compile_ground_problem(ground_problem, plan)

    print("RESA-RUNTIME {}".format(time.time() - start_time))
    
    if not os.path.isdir(output):
        os.system('mkdir {}'.format(output))
    
    w = PDDLWriter(compiled_problem)
    w.write_domain(output+"/compiled_dom.pddl")
    w.write_problem(output+"/compiled_prob.pddl")
    

if __name__ == '__main__':
    main()
