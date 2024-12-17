import os, sys
from os import listdir
from os.path import join, isfile
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

def create_a_predicate(action_name, plan, index):
    return unified_planning.model.Fluent("a_{}_{}_{}".format(action_name, plan, str(index)))

def create_p_predicate(index):
    return unified_planning.model.Fluent("p_{}".format(str(index)))

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

def create_done(i,j):
    return unified_planning.model.Fluent('done_p{}_a{}'.format(str(i),str(j)))


def compile_ground_problem(problem, plans):
    
    new_problem = unified_planning.model.Problem('repaired-ground')

    F = problem.fluents
    if len(problem.goals[0].args) != 0:
        G = list(problem.goals[0].args)
    else:
        G = problem.goals

    for g in G:
        new_problem.add_goal(g)


    I = problem.explicit_initial_values
    
    A = problem.actions
    
    done_atoms = [create_done(i,j) for i in range(0,len(plans)) for j in range(0, len(plans[i]))]

    w = unified_planning.model.Fluent('w', BoolType())

    q = unified_planning.model.Fluent('q', BoolType())

    plan_selected = unified_planning.model.Fluent('plan_selected', BoolType())

    costs : Dict[Action, Int]  = {}

    f_set = set()

    for i in range(0, len(plans)):
        f_set.add(create_p_predicate(i))

    f_set = f_set.union(done_atoms)
    f_set.add(w)
    f_set.add(q)
    f_set.add(plan_selected)

    print("creo A0")
    #A_0
    A0 = list()
    for i in range(0,len(plans)):
        for j in range(0, len(plans[i])):
            a = plans[i][j]
            if a is not None:
                name = a.name
                new_a = a.clone()
                new_a.name = name+"_p"+str(i)+"_a"+str(j)

                new_a.add_precondition(w)
                new_a.add_precondition(create_a_predicate(name,"p"+str(i),B(name,j,plans[i])))
                new_a.add_precondition(create_p_predicate(i))

                f_set.add(create_a_predicate(name,"p"+str(i), B(name,j,plans[i])))
                f_set.add(create_a_predicate(name,"p"+str(i), B(name,j,plans[i])+1))

                new_a.add_effect(create_a_predicate(name,"p"+str(i),B(name,j,plans[i])+1), True)
                new_a.add_effect(create_a_predicate(name,"p"+str(i),B(name,j,plans[i])), False) #not
                new_a.add_effect(create_done(i,j), True)

                costs[new_a] = Int(0)
                A0.append(new_a)

    print("creo A1")        
    #A1
    A1 = list()
    for a in A:
        name = a.name
        new_a = a.clone()
        new_a.name = name

        new_a.add_precondition(w)
        
        costs[new_a] = Int(1)
        A1.append(new_a)
    

    print("creo A3")
    #A3
    A3 = list()
    for i in range(0,len(plans)):
        for j in range(0, len(plans[i])):
            new_a = unified_planning.model.InstantaneousAction("act_done_p{}_a{}".format(str(i),str(j)))
            new_a.add_precondition(Not(w))
            new_a.add_precondition(Not(create_done(i,j)))
            new_a.add_precondition(create_p_predicate(i))
            new_a.add_effect(create_done(i,j), True)

            costs[new_a] = Int(1)
            A3.append(new_a)
    
    print("creo A4")
    #A4
    A4 = list()
    for i in range(0,len(plans)):
        new_a = unified_planning.model.InstantaneousAction("init_p{}".format(str(i)))

        new_a.add_precondition(Not(plan_selected))

        for a in set(plans[i]):
            if a is not None:    
                new_a.add_effect(create_a_predicate(a.name,"p"+str(i),0), True)

        new_a.add_effect(create_p_predicate(i), True)


        new_a.add_effect(plan_selected, True)

        costs[new_a] = Int(0) #costo ????????
        A4.append(new_a)
    
    print("creo A5")
    #A5
    A5 = list()
    for i in range(0,len(plans)):
        new_a = unified_planning.model.InstantaneousAction("plan_done_p{}".format(str(i)))

        new_a.add_precondition(create_p_predicate(i))
        for j in range(len(plans[i])):
            new_a.add_precondition(create_done(i,j))
        
        new_a.add_effect(q, True)
        costs[new_a] = Int(0)
        A5.append(new_a)


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
    new_problem.add_actions(A0+A1+A3+A4+A5)

    #Iprime
    I[w] = True
    Ikeys = list(I)
    for i in range(0, len(Ikeys)):
        new_problem.set_initial_value(Ikeys[i], I[Ikeys[i]])
    
    
    #Gprime
    new_problem.add_goal(q)


    #Metric
    metric = MinimizeActionCosts(costs, 0)
    new_problem.add_quality_metric(metric)

    return new_problem

def read_in_plan(problem, filename):
    actions = problem.actions
    #for act in actions:
    #    print("aaaa", act.name)
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


def convert_constraint(c):
    if c.kind == ds.ALWAYS:
        return ds.Always(convert_formula(c.gd1))
    elif c.kind == ds.SOMETIME:
        return ds.Sometime(convert_formula(c.gd1))
    elif c.kind == ds.ATMOSTONCE:
        return ds.AtMostOnce(convert_formula(c.gd1))
    elif c.kind == ds.SOMETIMEBEFORE:
        return ds.SometimeBefore(convert_formula(c.gd1), convert_formula(c.gd2))
    elif c.kind == ds.SOMETIMEAFTER:
        return ds.SometimeAfter(convert_formula(c.gd1), convert_formula(c.gd2))


def convert_ds_up(F, A, I, G):
    F_new = []
    I_new = []
    A_new = []

    ground_problem = unified_planning.model.Problem('ground')

    for atom in F:
        F_new.append(convert_formula(atom))
    for atom in I:
        I_new.append(convert_formula(atom))
    
    G_new = convert_formula(G)

    for action in A:
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
    
    #F
    print("inserisco F_new")
    for i in range(0, len(F_new)):
        ground_problem.add_fluent(F_new[i], default_initial_value=False)

    #A
    print("inserisco A_new")
    ground_problem.add_actions(A_new)

    #I
    for i in range(0, len(I_new)):
        ground_problem.set_initial_value(I_new[i], True)
    
    #G
    ground_problem.add_goal(G_new)
    
    return ground_problem




@click.command()
@click.argument('domain')
@click.argument('problem')
@click.argument('output')
@click.argument('plans_dir')
def main(domain, problem, output, plans_dir):

    print("Start")
    start_time = time.time()
    
    print("Grounding problem...")
    F, A, I, G, _ = ground(domain, problem)
    ground_problem = convert_ds_up(F, A, I, G)

    print("Reading plans...")
    plan_files = [f for f in os.listdir(plans_dir) if isfile(join(plans_dir, f))]
    plans = []
    for planname in plan_files:
        if planname.__contains__(".sol"):
            plans.append(read_in_plan(ground_problem, plans_dir+"/"+planname))

    
    print("Starting RESA")

    compiled_problem = compile_ground_problem(ground_problem, plans) 

    print("RESA-RUNTIME {}".format(time.time() - start_time))
    
    
    if not os.path.isdir(output):
        os.system('mkdir {}'.format(output))
    
    w = PDDLWriter(compiled_problem)
    w.write_domain(output+"/compiled_dom.pddl")
    w.write_problem(output+"/compiled_prob.pddl")

    
    

if __name__ == '__main__':
    main()
