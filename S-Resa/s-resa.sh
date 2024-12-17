#!/bin/sh

#cd $HOME/Resa/up_resa
prob=$(echo $2| tr '/' '\n' | tail -1)

#elimino quando non ci sono oggetti
sed 's/(:objects\s*\n\s*)//' $2 > prob_temp

#echo "Eseguo il file python"
python3 s-resa.py $1 prob_temp temp $4 > log

rm prob_temp

TIME=$(grep RUNTIME log | cut -d' ' -f2)

#se non esiste la cartella la creo
[ ! -d $3 ] && mkdir $3


mv temp/compiled_dom.pddl $3/domain-$prob 
mv temp/compiled_prob.pddl $3/$prob
echo -e "\n; Resa compilation time: $TIME" >> $3/$prob
