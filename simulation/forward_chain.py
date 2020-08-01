import collections as col
import re
from itertools import islice
from typing import Any, Dict, List, Tuple


def loadRules(fname_rules: str) -> List[Any]:
    """Loads rules from the file. If rules are set wrong in the file,
    it returns empty lists.

    Args:
        fname_rules (str): name of file from which we load rules

    Returns:
        List[Any]: namedtuples with these attributes:
            name - name of the rule
            conds - conditions to fulfil actions
            acts - actions (message, add or remove fact from the set of facts)
    """

    Rules = col.namedtuple("Rule", "name conds acts")
    rules = []

    # must contain non-whitespace character
    # must contain ?X in each comma seperated statement
    # must contain remove/add/message and ?X in each comma seperated statement
    patterns = [
        re.compile(r"\S+"),
        re.compile(r"((\?[A-Z]+)[^,]*, )*.*\?[A-Z].*"),
        re.compile(
            r"(((add)|(remove)|(message)) .*\?[A-Z][^,]*, )*"
            r"((add)|(remove)|(message)).*\?[A-Z].*"
        ),
    ]
    with open("simulation/knowledge/" + fname_rules + ".txt") as f1:
        while rule := [line.rstrip("\n:") for line in islice(f1, 4)]:
            if rule.pop():
                print("There is no empty line after rule!")
            for i in range(len(Rules._fields)):  # ? validation in while
                if not patterns[i].match(rule[i]):
                    print(Rules._fields[i], "field is set wrong!")
                    return []
            rules.append(Rules(*rule))

    return rules


def loadFacts(fname_facts: str) -> List[str]:
    """Loads facts from the file.

    Args:
        fname_facts (str): name of file from which we load facts

    Returns:
        List[str]: fact sentences
    """

    with open("simulation/knowledge/" + fname_facts + ".txt") as f:
        facts = [fact.rstrip() for fact in f]

    return facts


def findActions(rules: List[Any], facts: List[str]) -> List[List[str]]:
    """Finds all actions from given facts.

    Args:
        rules (List[Any]): namedtuples with these attributes:
            name - name of the rule (is not used for any purpose)
            conds - conditions for fulfilling rule's actions
            acts - actions (message, add or remove fact from the set of facts)
        facts (List[str]): fact sentences

    Returns:
        List[List[str]]: lists of actions that have been found from each rule
    """

    actions_found = []
    for rule in rules:  # LOOP over rules
        rule_acts = [act.split(" ", 1) for act in rule.acts.split(", ")]
        rule_acts_label = expand(rule.conds.split(), facts, {})
        for label in rule_acts_label:

            actions = []
            for type_, action in rule_acts:
                for key in [key.rstrip(",") for key in action.split()]:
                    if key.startswith("?"):
                        action = action.replace(key, label[key])
                actions.append(type_ + " " + action)

            actions_found.append(actions)

    return actions_found


def removeDuplicates(
    actions_found: List[List[str]], facts: List[str]
) -> List[List[str]]:
    """Removes the outcome of actions that were already present in the facts.

    Args:
        actions_found (List[List[str]]): lists of actions that have been
            found from each rule
        facts (List[str]): fact sentences

    Returns:
        List[List[str]]: lists of appliable actions
    """

    i = 0
    for _ in range(len(actions_found)):
        message = True  # happens when there wasnt a duplicate in prev acts
        j = 0
        for _ in range(len(actions_found[i])):
            type_, act = actions_found[i][j].split(" ", 1)
            if (
                (type_ == "add" and act in facts)
                or (type_ == "remove" and act not in facts)
                or (type_ == "message" and not message)
            ):
                del actions_found[i][j]
                message = False
            else:
                j += 1
        if not actions_found[i]:
            del actions_found[i]
        else:
            i += 1

    return actions_found


def applyActions(
    actions_appliable: List[List[str]], facts: List[str]
) -> Tuple[List[str], List[str]]:
    """Applies list of actions that are first in the queue.

    Args:
        actions_appliable (List[List[str]]): lists of appliable actions
        facts (List[str]): fact sentences

    Returns:
        Tuple[List[str], List[str]]: new fact sentences, messages
    """

    messages = []
    for action in actions_appliable[0]:
        type_, act = action.split(" ", 1)
        if type_ == "add":
            facts.append(act)
        elif type_ == "remove":
            facts.remove(act)
        elif type_ == "message":
            messages.append(act)

    return facts, messages


def expand(
    conds: List[str], facts: List[str], label: Dict[str, str]
) -> List[Dict[str, str]]:
    """Loops over conditions of a rule recursively and finds all
    condition-matching labels from given facts.

    Args:
        conds (List[str]): conditions for fulfilling rule's actions
        facts (List[str]): fact sentences
        label (Dict[str, str]): represent entities (?X -> <entity from fact>)

    Returns:
        List[Dict[str, str]]: labels
    """

    # LOOP over facts
    labels = []
    for fact_str in facts:
        fact_list = fact_str.split()
        tmp_label = {}
        continue_ = True
        for i, (c, f) in enumerate(zip(conds, fact_list)):
            c_key = c.rstrip(",")
            # label checking for "?"
            if c_key.startswith("?") and f[0].isupper():  # new entity
                if c_key not in label:
                    if f not in label.values():
                        tmp_label[c_key] = f
                    else:
                        continue_ = False
                elif label[c_key] != f:
                    continue_ = False
            # key identity checking with <> special cond
            elif c_key.startswith("<"):
                if label[conds[i + 1]] == label[conds[i + 2]]:
                    continue_ = False
            # unmatched condition with fact
            elif c_key != f:
                continue_ = False

            if not continue_:
                break

            # next condition -> recursive call
            if c.endswith(","):
                labels += expand(conds[i + 1 :], facts, {**label, **tmp_label})

        # label match found for action
        if continue_ and not c.endswith(","):
            labels.append({**label, **tmp_label})
            if c == "<>":  # iterating facts are irelevant as its independent
                break

    return labels


def saveFacts(facts: List[str], save_fname_facts: str) -> None:
    """Save facts into text file.

    Args:
        facts (List[List[str]]): list of new found facts
        save_fname_facts (str): name of the file
    """

    with open("simulation/knowledge/" + save_fname_facts + ".txt", "w") as f:
        f.write("\n".join(facts))


def runProduction(pars: Dict[str, Any]) -> None:
    """Finds a solution and saves it to text file.

    Args:
        pars (Dict[str, Any]): parameters that contain these string values:
            save_fname_facts (str): name of file into which facts will be saved
            load_fname_facts (str): name of file from which we load facts
            load_fname_rules (str): name of file from which we load rules
            step_by_step (bool): entering one fact by each Production run
    """

    rules = loadRules(pars["load_fname_rules"])
    facts = loadFacts(pars["load_fname_facts"])

    if pars["step_by_step"]:
        found_facts = []  # type: List[str]
        for i, fact in enumerate(facts):
            found_facts = runForwardChain(
                found_facts + [fact], rules, pars["save_fname_facts"]
            )
    else:
        runForwardChain(facts, rules, pars["save_fname_facts"])


def runForwardChain(
    facts: List[str], rules: List[Any], save_fname_facts: str
) -> List[str]:
    """Finds a solution and saves it to the text file.

    Args:
        facts (List[str]): fact sentences
        rules (List[Any]): namedtuples with these attributes:
            name - name of the rule
            conds - conditions to fulfil actions
            acts - actions (message, add or remove fact from the set of facts)
        save_fname_facts (str): name of the file into which facts will be saved

    Returns:
        List[str]: fact sentences
    """

    # LOOP over to-be FACTS
    while True:
        actions_found = findActions(rules, facts)
        actions_appliable = removeDuplicates(actions_found, facts)

        if not actions_appliable:
            saveFacts(facts, save_fname_facts)
            break

        facts, msgs = applyActions(actions_appliable, facts)
        for fact in facts:
            print(fact)
        for msg in msgs:
            print("MESSAGE:", msg)
        print()

    return facts


if __name__ == "__main__":

    chain_parameters = dict(
        save_fname_facts="facts",
        load_fname_facts="facts_init",
        load_fname_rules="rules",
        step_by_step=True,
    )

    runProduction(chain_parameters)