#!/bin/sh
#cd $HOME/Resa/up_resa
prob=$(echo $2| tr '/' '\n' | tail -1)

#elimino quando non ci sono oggetti
sed 's/(:objects\s*\n\s*)//' $2 > prob_temp

if [[ "$1" == *"spider"* ]];
    then
        sed 's/(:action /(:action a-c-t-/g' $1 > dom_temp
        sed 's/(\s*/(a-c-t-/g' $4 > sol_temp
    else 
        cat $1 > dom_temp
        cat $4 > sol_temp
    fi

sed '/;/d' dom_temp > dom_temp.tmp
mv dom_temp.tmp dom_temp

#echo "Eseguo il file python"
python3 ./l-resa.py dom_temp prob_temp temp sol_temp > log

rm prob_temp

TIME=$(grep RUNTIME log | cut -d' ' -f2)

#se non esiste la cartella la creo
[ ! -d $3 ] && mkdir $3

#Sostituisco gli oggetti
objects=$(pcregrep -M --only-matching --buffer-size 200000 '\(:objects[\s\S]*\)\s*\(:init' $2)

objects=$(echo "$objects" | sed 's/(:init//g')
 
objects=$(echo "$objects" | sed 's/-/_/g')
objects=$(echo "$objects" | sed 's/ _ / - /g')

constants_p=$(echo "$objects" | sed 's/(:objects/(:constants /g')


#echo "cost p"
#echo "$constants_p"

#elimino gli oggetti dal nuovo problema 
sed 's/(:objects\s*.*\s*)\s*(:init/(:init/' temp/compiled_prob.pddl > temp/compiled_prob.pddl.tmp
mv temp/compiled_prob.pddl.tmp temp/compiled_prob.pddl

#elimino le costanti dal nuovo dominio
sed 's/(:constants\s*.*\s*)\s*(:predicates/(:predicates/' temp/compiled_dom.pddl > temp/compiled_dom.pddl.tmp
mv temp/compiled_dom.pddl.tmp temp/compiled_dom.pddl

tail=$(pcregrep --only-matching --buffer-size 1000000 -M '\(:predicates[\s\S]*$' temp/compiled_dom.pddl)

constants_d=$(pcregrep -M --only-matching --buffer-size 200000 '\(:constants[\s\S]*\)\s*\(:predicates' dom_temp)


sed '/(:predicates/,$d' temp/compiled_dom.pddl > temp/compiled_dom.pddl.tmp
mv temp/compiled_dom.pddl.tmp temp/compiled_dom.pddl

#elimino tonda alla fine
constants_p=$(echo "$constants_p" | sed 's/)//g')
echo "$constants_p" >> temp/compiled_dom.pddl

constants_d=$(echo "$constants_d" | sed 's/(:predicates//g')
constants_d=$(echo "$constants_d" | sed 's/(:constants/\n/g')
constants_d=$(echo "$constants_d" | sed 's/)//g')

#echo "cost d"
#echo "$constants_d"

echo  "$constants_d" >> temp/compiled_dom.pddl
echo  ")" >> temp/compiled_dom.pddl

echo "$tail" >> temp/compiled_dom.pddl

#sed -i 's/(total_cost)/(total-cost)/' temp/compiled_dom.pddl
#sed -i 's/(increase\s*(total-cost)\s*0)\s*(increase\s*(total-cost)\s*1)/(increase (total-cost) 1)/' temp/compiled_dom.pddl
#sed -i 's/(total_cost)/(total-cost)/' temp/compiled_prob.pddl
sed 's/:numeric-fluents//' temp/compiled_dom.pddl > temp/compiled_dom.pddl.tmp
mv temp/compiled_dom.pddl.tmp temp/compiled_dom.pddl

mv temp/compiled_dom.pddl $3/domain-$prob
mv temp/compiled_prob.pddl $3/$prob
echo -e "\n; Resa compilation time: $TIME" >> $3/$prob
