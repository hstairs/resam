import os, sys
import shutil
from os import path
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
import string,random
from downward.FDgrounder import ground
from downward.FDgrounder import pddl

SEPARATOR = "#"

def create_p_predicate(action_name, index):
    return unified_planning.model.Fluent("p_{}_{}".format(action_name,str(index)))

def create_not_p_predicate(action_name, index):
    return unified_planning.model.Fluent("p_{}_{}".format(action_name,str(index)))

def get_lifted_preconditions(a_plan, problem_objects, problem_fluents):
    lifted_pre = []
    ground_pre = a_plan.preconditions

    for p in ground_pre:
        str_p = str(p)
        if(str_p.__contains__("not")):
            value = False
            str_p = str_p.replace("(", " ").replace(")"," ").replace(" not ","").strip()
        else:
            value = True
        split = str_p.split(SEPARATOR)
        fluent_name = split[0]
        parameters = split[1:]
        for f in problem_fluents:
            #print("f name",f.name)
            if(f.name == fluent_name):
                pre_params = [o for par in parameters for o in problem_objects if par == o.name]
                if len(parameters)>0:
                    if(value):
                        lifted_pre.append(f(*pre_params))
                    else:
                        lifted_pre.append(Not(f(*pre_params)))
                else:
                    if(value):
                        lifted_pre.append(f)
                    else:
                        lifted_pre.append(Not(f))
    return lifted_pre

def get_lifted_effects(a_plan, problem_objects, problem_fluents):
    lifted_eff = []
    ground_eff = a_plan.effects

    for e in ground_eff:
        #print(e.fluent)
        split = str(e.fluent).split(SEPARATOR)
        value = e.value
        fluent_name = split[0]
        parameters = split[1:]
        #print(fluent_name, parameters, value)
        for f in problem_fluents:
            if(f.name == fluent_name):
                eff_params = [o for par in parameters for o in problem_objects if par == o.name]
                #print(eff_params)
                lifted_eff.append([f(*eff_params), value])
    return lifted_eff
    

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


def create_predicate_not_and_eq(vars, parameters):
    array_eq = []
    for i in range(0, len(vars)):
        array_eq.append(Equals(vars[i], parameters[i]))
    return Not(And(array_eq))

def delete_all_metrics(problem):
    #delete increase effects
    for a in problem.actions:
        for e in a.effects:
            if(e.kind == EffectKind.INCREASE):
                a.effects.remove(e)
    
    problem.clear_quality_metrics()
    return problem

def clone_initial_state(problem):
    init = {}
    for key in problem.explicit_initial_values:
        if(not(problem.explicit_initial_values[key].is_int_constant())):
            init[key] = problem.explicit_initial_values[key]
    return init

def compile_hybrid_problem(problem, plan):


    #print(problem.quality_metrics)

    problem = delete_all_metrics(problem)

    I = clone_initial_state(problem)

    

    user_types = []
    for i in range(0, len(problem.user_types)):
        user_types.append(UserType(str(problem.user_types[i])))
    
    new_problem = unified_planning.model.Problem('repaired-hybrid')

    problem_objects = problem.all_objects
    #new_problem.add_objects(problem_objects)

    problem_fluents = problem.fluents

    new_problem._user_types = problem.user_types

    F = problem.fluents
    for fluent in problem.fluents:
        if fluent not in F:
            F.append(fluent)

    if str(problem.goals[0]).__contains__("and"):
        G = list(problem.goals[0].args)
    else:
        G = problem.goals
    
    
    #print(G)
    for g in G:
        new_problem.add_goal(g)

    

    p_g = plan

    
    split = [plan[i].name.split(SEPARATOR) for i in range(0, len(plan))]

    act_param = []
    for a in problem.actions:
        if(len(a.parameters)>=1):
            act_param.append([a.name, a.parameters])
    
    objects = str(problem.all_objects)

    #print(problem_objects)
    params = []
    for t in range(0, len(split)):
        for k in range(0, len(act_param)):
            if(split[t][0] == act_param[k][0]):
                row = []
                for l in range(0, len(act_param[k][1])):
                    #print(split[t][l+1], act_param[k][1][l].type)
                    for ob in problem_objects:
                        if str(ob) == split[t][l+1]:
                            row.append(ob)
                    if split[t][l+1] not in objects:
                        #new_problem.add_object(split[t][l+1], act_param[k][1][l].type)
                        objects.append(split[t][l+1])
                params.append([act_param[k][0], row])



    done_atoms = [unified_planning.model.Fluent('done_{}'.format(i), BoolType()) for i in range(0,len(p_g))]
    w = unified_planning.model.Fluent('w', BoolType())

    costs : Dict[Action, Int]  = {}

    f_set = set()
    f_set = f_set.union(done_atoms)
    f_set.add(w)

    #creo fatti act_isinplan
    f_isinplan = []
    for a in problem.actions:
        if(len(a.parameters)>=1):
            act_isinplan = unified_planning.model.Fluent(a.name+"_isinplan", BoolType(), a.parameters)
            f_set.add(act_isinplan)
            f_isinplan.append(act_isinplan)
    
    
    
    #imposto gli stati iniziali dei fatti act_isinplan sulla base delle azioni presenti nel piano
    for i in range(0,len(params)):
        for j in range(0, len(f_isinplan)):
            #print(str(f_isinplan[j].name).split("_isinplan")[0])
            if(params[i][0] == str(f_isinplan[j].name).split("_isinplan")[0]):
                #print(params[i], f_isinplan[j], *params[i][1])
                I[f_isinplan[j](*params[i][1])] = True
    
    #print(I) 
            

    

    #A_0
    A0 = list()
    for i in range(0,len(p_g)):
        a_plan = p_g[i]
        if a_plan is not None:
            name = a_plan.name
            new_a = unified_planning.model.InstantaneousAction(name)

            pre = get_lifted_preconditions(a_plan, problem_objects, problem_fluents)
            
            for p in pre:
                new_a.add_precondition(p)

            eff = get_lifted_effects(a_plan, problem_objects, problem_fluents)

            #print(eff)

            #print(a_plan)
            added_effects = []
            for e in eff:
                e_fluent = e[0]
                e_value = e[1]
                if e_fluent not in added_effects:
                    new_a.add_effect(e_fluent, e_value)
                    added_effects.append(e_fluent)

            new_a.name = name+SEPARATOR+str(i)

            new_a.add_precondition(w)
            new_a.add_precondition(create_p_predicate(name,B(name,i,p_g))) #da testare con altri problemi

            f_set.add(create_p_predicate(name,B(name,i,p_g)))
            f_set.add(create_p_predicate(name,B(name,i,p_g)+1))

            new_a.add_effect(create_p_predicate(name,B(name,i,p_g)+1), True)
            new_a.add_effect(create_not_p_predicate(name, B(name,i,p_g)), False)
            new_a.add_effect(create_done(i), True)

            costs[new_a] = Int(0)
            A0.append(new_a)

    #A1
    A1 = list()
    j = 0
    for a in problem.actions:
        if(len(a.parameters)>=1):
            name = a.name
            new_a = a.clone()
            new_a.clear_preconditions()
            #pre = a.preconditions[0].args

            if str(a.preconditions[0]).__contains__("and"):
                pre = list(a.preconditions[0].args)
            else:
                pre = a.preconditions

            for p in pre:
                new_a.add_precondition(p)

            new_a.add_precondition(w)
            chars = []
            for i in range(len(a.parameters)):
                letters = string.ascii_lowercase
                result_str = ''.join(random.choice(letters) for i in range(3))
                chars.append(result_str)
            
            vars = []
            for k in range(0, len(a.parameters)):
                vars.append(Variable(chars[k], a.parameters[k].type))
            
            
            new_a.add_precondition(Forall(Implies(f_isinplan[j](*vars), create_predicate_not_and_eq(vars, new_a.parameters)), *vars))

            costs[new_a] = Int(1)

            A1.append(new_a)
            j=j+1

            
    #A2
    A2 = list()
    for a_plan in set(p_g):
        if a_plan is not None:
            I[create_p_predicate(a_plan.name,0)] = True

            name = a_plan.name
            #new_a = a.clone()

            new_a = unified_planning.model.InstantaneousAction(name)

            pre = get_lifted_preconditions(a_plan, problem_objects, problem_fluents)
            

            for p in pre:
                new_a.add_precondition(p)

            eff = get_lifted_effects(a_plan, problem_objects, problem_fluents)


            added_effects = []
            for e in eff:
                e_fluent = e[0]
                e_value = e[1]
                if e_fluent not in added_effects:
                    new_a.add_effect(e_fluent, e_value)
                    added_effects.append(e_fluent)

            new_a.add_precondition(w)

            costs[new_a] = Int(1)
            A2.append(new_a)
    
    #A3
    A3 = list()
    Gprime = []
    for i in range(0,len(p_g)):
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

    #print(I)
    #Iprime
    I[w] = True
    Ikeys = list(I)
    for i in range(0, len(Ikeys)):
        #print(Ikeys[i], I[Ikeys[i]])
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
    #for act in actions:
    #    print("aaaa", act.name)
    with open(filename) as f:
        for a in f.readlines():     
            if ";" not in a:  
                a = a.replace(" )",")").replace("( ", "(")
                a = a.replace("(","").replace(")","").replace(" ",SEPARATOR).strip()
                found = False
                for act in actions:
                    if str(act.name).__eq__(str(a)):
                        plan.append(act)
                        found = True
                if found == False:
                    #plan.append(None)
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



def convert_ds_up(F, A, I, G, filename):
    F_new = []
    I_new = []
    A_new = []
    for atom in F:
        F_new.append(convert_formula(atom))
    for atom in I:
        I_new.append(convert_formula(atom))
    
    G_new = convert_formula(G)

    plan = list()
    with open(filename) as f:
        for a in  f.readlines():     
            if ";" not in a:            
                #a = a.replace("(","").replace(")","").replace(" ","_").strip()
                plan.append(a.replace("\n",""))
                
    for action in A:
        if str(action.name) in plan:
            preconditions = [convert_formula(pre) for pre in action.precondition]

            new_a = unified_planning.model.InstantaneousAction(action.name.replace("( ","(").replace(" )",")").replace(' ', SEPARATOR).replace('(', '').replace(')',''))
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
    
    #print(F_new, I_new, A_new, G_new, C_new)
    ground_problem = unified_planning.model.Problem('ground')

    #F
    for i in range(0, len(F_new)):
        ground_problem.add_fluent(F_new[i], default_initial_value=False)

    #A
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
@click.argument('planname')
def main(domain, problem, output, planname):

    print("Start")
    start_time = time.time()

    print("Grounding problem...")
    F, A, I, G, _ = ground(domain, problem)
    ground_problem = convert_ds_up(F, A, I, G, planname)

    print("Reading plan...")

    plan = read_in_plan(ground_problem, planname)

    print("Starting RESA")
    reader = PDDLReader()
    problem = reader.parse_problem(domain, problem)
    compiled_problem = compile_hybrid_problem(problem, plan)

    print("RESA-RUNTIME {}".format(time.time() - start_time))


    if not os.path.isdir(output):
        os.system('mkdir {}'.format(output))

    print("Writing in file...")
    w = PDDLWriter(compiled_problem)
    w.write_domain(output+"/compiled_dom.pddl")
    print("Domain file written!")
    w.write_problem(output+"/compiled_prob.pddl")
    print("Problem file written!")



if __name__ == '__main__':
    main()
