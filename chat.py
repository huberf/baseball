import spacy
import re
import json
from collections import defaultdict

# Set up script wide values
QUESTION_SYMB = '<?>'
months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

# Set up data
nlp = spacy.load('en_core_web_sm')
database = json.loads(open('baseball_data.json', 'r').read())
teams = list(set([i['home_team'] for i in database]))
# add losing team value
for i,val in enumerate(database):
    val['losing_team'] = val['home_team'] if val['away_team'] == val['winning_team'] else val['away_team']
    database[i] = val

''' System works by mapping search keys to properties of the data list
'''
criteria_to_key = {
        'team': ['home_team', 'away_team'],
        'winner': ['winning_team'],
        'loser': ['losing_team'],
        'location': ['location'],
        'time': ['month', 'day', 'year'],
        'month': ['month'],
        'game_count': [None],
        'team_count': [None]
        }

''' Given a template as defined by the search criteria, identify all relevant
    documents.
'''
def perform_search(search):
    global database, criteria_to_key
    criteria = search['criteria']
    segmented_found = defaultdict(list)
    # go entry by entry
    for entry in database:
        passes_all = True
        answers = []
        passing_criteria = [] # to store relevant criteria for "counting" based upon segmentation
        # for each criteria (i.e. schematic key) verify proper matching
        for criterion in criteria:
            keys = criteria_to_key[criterion]
            for key in keys:
                if key == None:
                    break
                if not criteria[criterion] == QUESTION_SYMB:
                    if not entry[key] == criteria[criterion]:
                        passes_all = False
                        break
                else:
                    answers.append((key, entry[key]))
                passing_criteria.append(entry[key])
        if passes_all:
            segmented_found[tuple(passing_criteria)].append((answers, entry))
    # now process matched records for high level count style criteria
    numeric_answer = []
    final_segment_return = {}
    for i in segmented_found:
        # handle the game count template
        if 'game_count' in criteria:
            if not criteria['game_count'] == QUESTION_SYMB:
                val = criteria['game_count']

                if len(segmented_found[i]) == criteria['game_count']:
                    final_segment_return[i] = segmented_found[i]
            else:
                final_segment_return[i] = segmented_found[i]
                numeric_answer.append('{}: {} games'.format(i, len(segmented_found[i])))
        else:
            final_segment_return[i] = segmented_found[i]
    return (final_segment_return, numeric_answer)

''' Checks whether the query conforms to the limitations of the template
    approach.
'''
def query_safe(raw_str):
    illegal_logical = ['and', 'or', 'not']
    illegal_connections = ['most', 'highest', 'greatest']
    if sum([i in raw_str for i in illegal_logical]):
        return False
    if sum([i in raw_str for i in illegal_connections]):
        return False
    if len(raw_str) == 0 or raw_str[0] == '\n':
        return False
    return True

def get_pps(doc):
    ''' Gets prepositional phrases from document'''
    pps = []
    for token in doc:
        if token.pos_ == 'ADP':
            pp = ' '.join([tok.orth_ for tok in token.subtree])
            pps.append(pp)
    return pps

''' Identifies and fills in the template for the ultimate search through the
    database.
'''
def process_query(raw_str):
    global nlp
    # First do replacement and expansion
    replacements = {}
    for month in months:
        replacements[month[:3] + ' '] = month
    # Now do actual replacement
    for trigger in replacements:
        raw_str = raw_str.replace(trigger, replacements[trigger])

    query = {}
    wrds = raw_str.split(' ')

    # Check if query does not have question words
    question_words = ['who', 'where', 'what', 'how']
    is_true_false = 0 == sum([i.lower() in question_words for i in wrds])
    query['result_tf'] = True

    doc = nlp(raw_str)
    noun_phrases = list(doc.noun_chunks)
    prepositional_phrases = get_pps(doc)
    '''
    print('np', noun_phrases)
    print('pp', prepositional_phrases)
    print('ents', [(i, i.label_) for i in doc.ents])
    print('doc', doc)
    '''

    criteria = content_analysis(raw_str, wrds, noun_phrases, prepositional_phrases, doc.ents)
    query['criteria'] = criteria
    return query

''' Given the more Chomsky esque analysis and break down of the query
    now employ the templatized paradigm.
    For baseball this primarily entails identifying applicable subroutines which
    then execute modifications on the search criteria.
'''
def content_analysis(raw_str, wrds, np, pp, ents):
    global months, teams
    # now fill out criteria
    criteria = {}

    lower_first = wrds[0].lower()
    if lower_first == 'where':
        criteria['location'] = QUESTION_SYMB
    if lower_first == 'when':
        criteria['time'] = QUESTION_SYMB

    REGEX_VAL_INT = 'regex_val_int'
    REGEX_VAL = 'regex_val'
    subroutines =[
            ('exact', 'what team', ('team', QUESTION_SYMB)),
            ('exact', 'how many games', ('game_count', QUESTION_SYMB)),
            ('exact', 'who won', ('winner', QUESTION_SYMB)),
            ('exact', 'who lost', ('winner', QUESTION_SYMB)),
            ('re', '([0-9]*) games', ('game_count', REGEX_VAL_INT))
            ]
    for sub in subroutines:
        if sub[0] == 'exact':
            if sub[1] in raw_str.lower():
                criteria[sub[2][0]] = sub[2][1]
        elif sub[0] == 're':
            result = re.search(sub[1], raw_str.lower())
            if result:
                val = result[1]
                if sub[2][1] == REGEX_VAL_INT:
                    val = int(val)
                # modify by existance of range value
                if 'less than' in raw_str.lower():
                    criteria[sub[2][0]] = '<' + str(val)
                elif 'more than' in raw_str.lower():
                    criteria[sub[2][0]] = '>' + str(val)
                else:
                    criteria[sub[2][0]] = val

    # now do date extraction
    for ent in ents:
        val = str(ent)
        if ent.label_ == 'DATE':
            for month in months:
                if month in val:
                    criteria['month'] = month
    # now handle the team template
    for phrase in np:
        phrase = str(phrase)
        for team in teams:
            if team in phrase:
                if 'win' in raw_str.lower() or 'beat' in raw_str.lower():
                    criteria['winner'] = team
                elif 'lose' in raw_str.lower():
                    criteria['loser'] = team
                else:
                    criteria['team'] = team

                if 'lose to' in raw_str.lower():
                    criteria['winner'] = QUESTION_SYMB
                if 'win to' in raw_str.lower() or 'beat' in raw_str.lower():
                    criteria['loser'] = QUESTION_SYMB
    return criteria

''' Display the results to the user as specified in the program
'''
def display_results(results):
    # show results to user
    if len(results[1]) > 0:
        print('Numeric result(s):')
        for i in results[1]:
            print(i)
    else:
        for key in results[0]:
            print(key)
            for val in results[0][key]:
                print('\t' + str(val[0]))

if __name__ == '__main__':
    while True:
        query = input('> ')
        if not query_safe(query):
            print('Invalid query supplied.')
            continue
        search = process_query(query)
        print('Spec list:', search['criteria'])
        has_q = not 0 == sum([search['criteria'][i] == QUESTION_SYMB for i in search['criteria']])
        if not has_q: # i.e. nothing to search for
            print('No query discovered. Try rephrasing.\n')
            continue
        results = perform_search(search)
        display_results(results)
        print()

