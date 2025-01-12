#/u/GoldenSights
import praw
import time
import sqlite3

'''USER CONFIGURATION'''

USERNAME  = ""
#This is the bot's Username. In order to send mail, he must have some amount of Karma.
PASSWORD  = ""
#This is the bot's Password. 
USERAGENT = ""
#This is a short description of what the bot does. For example "/u/GoldenSights' Newsletter bot"
SUBREDDIT = "GoldTesting"
#This is the sub or list of subs to scan for new posts. For a single sub, use "sub1". For multiple subreddits, use "sub1+sub2+sub3+..."
PARENTSTRING = ["Solution Verified"]
#These are the words you are looking for. If User says this, Parent gets 1 point in his flair
REPLYSTRING = "You have awarded one point to _parent_"
#This is the phrase that User will receive
#_parent_ will be replaced by the username of the Parent.
EXEMPT = []
#Any usernames in this list will not receive points. Perhaps they have special flair.

OPONLY = True
#Is OP the only person who can give points?
#I recommend setting this to False. Other users might have the same question and would like to reward a good answer.

MAXPERTHREAD = 200
#How many points can be distributed in a single thread?
EXPLAINMAX = True
#If the max-per-thread is reached and someone tries to give a point, reply to them saying that the max has already been reached
EXPLAINREPLY = "Sorry, but " + str(MAXPERTHREAD) + " point(s) have already been distributed in this thread. This is the maximum allowed at this time."
#If EXPLAINMAX is True, this will be said to someone who tries to give a point after max is reached

MAXPOSTS = 100
#This is how many posts you want to retrieve all at once. PRAW can download 100 at a time.
WAIT = 20
#This is how many seconds you will wait between cycles. The bot is completely inactive during this time.


'''All done!'''



WAITS = str(WAIT)
try:
	import bot #This is a file in my python library which contains my Bot's username and password. I can push code to Git without showing credentials
	USERNAME = bot.uG
	PASSWORD = bot.pG
	USERAGENT = bot.aG
except ImportError:
    pass

sql = sqlite3.connect('sql.db')
print('Loaded SQL Database')
cur = sql.cursor()

cur.execute('CREATE TABLE IF NOT EXISTS oldposts(ID TEXT)')
cur.execute('CREATE TABLE IF NOT EXISTS submissions(ID TEXT, count INT)')
print('Loaded Completed table')

sql.commit()

r = praw.Reddit(USERAGENT)
r.login(USERNAME, PASSWORD) 

def flair(subreddit, username):
	#Subreddit must be the sub object, not a string
	#Returns True if the operation was successful
	success = False
	print('\tChecking flair for ' + username)
	flairs = subreddit.get_flair(username)
	flairs = flairs['flair_text']
	if flairs != None and flairs != '':
		print('\t -' + flairs)
		try:
			flairs = int(flairs)
			flairs += 1
			flairs = str(flairs)
			success = True
		except ValueError:
			print('\tCould not convert flair to a number.')
	else:
		print('\tNo current flair. 1 point')
		flairs = '1'
		success = True
	print('\tAssigning Flair: ' + flairs)
	subreddit.set_flair(username, flairs)
	if success == True:
		return True
	else:
		return False


def scan():
	print("Scanning " + SUBREDDIT)
	subreddit = r.get_subreddit(SUBREDDIT)
	comments = subreddit.get_comments(limit=MAXPOSTS)
	for comment in comments:
		cid = comment.id
		#Check if it's in the database
		cur.execute('SELECT * FROM oldposts WHERE ID=?', [cid])
		if not cur.fetchone():
			print(cid)
			cbody = comment.body.lower()
			#Check if it has the keyword
			if any(flag.lower() in cbody for flag in PARENTSTRING):
				print('\tFlagged.')
				#Check if it's a root
				if not comment.is_root:
					try:
						print('\tFetching parent and Submission data.')
						cauthor = comment.author.name
						parentcom = r.get_info(thing_id=comment.parent_id)
						pauthor = parentcom.author.name
						op = comment.submission.author.name
						opid = comment.submission.id
						#Check if the person is giving points to himself
						if pauthor != cauthor:
							#Check if the person is Exempt
							if not any(exempt.lower() == pauthor.lower() for exempt in EXEMPT):
								moderators = subreddit.get_moderators()
								mods = []
								for moderator in moderators:
									mods.append(moderator.name)
								#Pass anyone if OPONLY is False. Pass only OP or moderators when OPONLY is True
								if OPONLY == False or cauthor == op or cauthor in mods:
									cur.execute('SELECT * FROM submissions WHERE ID=?', [opid])
									fetched = cur.fetchone()
									#Check if this submission is in the database. Add it if not
									if not fetched:
										cur.execute('INSERT INTO submissions VALUES(?, ?)', [opid, 0])
										fetched = 0
									else:
										fetched = fetched[1]
									#Check if too many points have been given out yet
									if fetched < MAXPERTHREAD:
										#Attempt to do flair
										if flair(subreddit, pauthor):
											print('\tWriting reply')
											comment.reply(REPLYSTRING.replace('_parent_', pauthor))
											cur.execute('UPDATE submissions SET count=? WHERE ID=?', [fetched+1, opid])
									else:
										print('\tMaxPerThread has been reached')
										if EXPLAINMAX == True:
											print('\tWriting reply')
											comment.reply(EXPLAINREPLY)
								else:
									print('\tOther users cannot give points.')
							else:
								print('\tParent is on the exempt list.')
						else:
							print('\tCannot give points to self.')
					except AttributeError:
						print('\tCould not fetch usernames. Cannot proceed.')
				else:
					print('\tRoot comment. Ignoring.')


			cur.execute('INSERT INTO oldposts VALUES(?)', [cid])
		sql.commit()
	
while True:
	scan()
	print('Running again in ' + WAITS + ' seconds.\n')
	time.sleep(WAIT)