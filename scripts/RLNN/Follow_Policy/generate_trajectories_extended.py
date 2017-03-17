#!/usr/bin/env python

from variables import *

def modify_trans_mat():
	global trans_mat
	epsilon = 0.0001
	for i in range(0,action_size):
		trans_mat[i][:][:] += epsilon
		trans_mat[i] /= trans_mat[i].sum()

def initialize_model_bucket():
	global cummulative, bucket_index, bucket_space
	orig_mat = copy.deepcopy(trans_mat)
	dummy = copy.deepcopy(trans_mat)
	for k in range(0,action_size):		
		orig_mat = trans_mat[k,:,:]

		for i in range(0,transition_space):
			for j in range(0,transition_space):				
				cummulative[k] += orig_mat[i,j]
				bucket_space[k,transition_space*i+j] = cummulative[k]
				dummy[k,i,j] = cummulative[k]

	print "BUCKET SPACE: ", dummy, "BUCKET SPACE."

def remap_indices(bucket_index):

	#####action_space = [[-1,0],[1,0],[0,-1],[0,1],[-1,-1],[-1,1],[1,-1],[1,1]]
	#####UP, DOWN, LEFT, RIGHT, UPLEFT, UPRIGHT, DOWNLEFT, DOWNRIGHT..

	if (bucket_index==0):
		return 4
	elif (bucket_index==1):
		return 0
	elif (bucket_index==2):
		return 5
	elif (bucket_index==3):
		return 2	
	elif (bucket_index==5):
		return 3
	elif (bucket_index==6):
		return 6
	elif (bucket_index==7):
		return 1
	elif (bucket_index==8):
		return 7
	elif (bucket_index==4):
		return 8

def simulated_model(action_index):
	global trans_mat, from_state_belief, bucket_space, bucket_index, cummulative
	rand_num = random.random()

	if (rand_num<bucket_space[action_index,0]):
		bucket_index=0
	
	for i in range(1,transition_space**2):
		if (bucket_space[action_index,i-1]<=rand_num)and(rand_num<bucket_space[action_index,i]):
			bucket_index=i

	remap_index = remap_indices(bucket_index)

	if (bucket_index!=((transition_space**2)/2)):
		current_pose[0] += action_space[remap_index][0]
		current_pose[1] += action_space[remap_index][1]

	if (current_pose[0]>49):
		current_pose[0]=49
	if (current_pose[1]>49):
		current_pose[1]=49
	if (current_pose[0]<0):
		current_pose[0]=0
	if (current_pose[1]<0):
		current_pose[1]=0
		
def initialize_observation():
	global observation_model
	observation_model = npy.array([[0.,0.05,0.],[0.05,1.6,0.05],[0.,0.05,0.]])	
	epsilon=0.0001
	observation_model += epsilon
	observation_model /= observation_model.sum()

	print observation_model

def initialize_obs_model_bucket():
	global obs_bucket_space, observation_model, obs_space, obs_cummulative
	for i in range(0,obs_space):
		for j in range(0,obs_space):
			obs_cummulative += observation_model[i,j]
			obs_bucket_space[obs_space*i+j] = obs_cummulative

	print obs_bucket_space

def initialize_all():
	initialize_observation()
	initialize_obs_model_bucket()
	modify_trans_mat()
	initialize_model_bucket()

def simulated_observation_model():
	global observation_model, obs_bucket_space, obs_bucket_index, observed_state, current_pose
	
	remap_index = 0
	rand_num = random.random()
	if (rand_num<obs_bucket_space[0]):
		obs_bucket_index=0
	
	for i in range(1,obs_space**2):
		if (obs_bucket_space[i-1]<=rand_num)and(rand_num<obs_bucket_space[i]):
			obs_bucket_index=i
	
	obs_bucket_index = int(obs_bucket_index)
	observed_state = copy.deepcopy(current_pose)

	if (obs_bucket_index!=((obs_space**2)/2)):
		remap_index = remap_indices(obs_bucket_index)
		observed_state[0] += action_space[remap_index,0]
		observed_state[1] += action_space[remap_index,1]

	if (observed_state[0]>49):
		observed_state[0]=49
	if (observed_state[1]>49):
		observed_state[1]=49
	if (observed_state[0]<0):
		observed_state[0]=0
	if (observed_state[1]<0):
		observed_state[1]=0

print optimal_policy

def follow_policy():
	global observed_state, current_pose, trajectory_lengths, trajectories
	state_counter=1	
	demo_counter=1
	
 	new_demo='y'
	act_ind = 0.
	max_demo = 50

	while (demo_counter<max_demo-2):
	
		ax = random.randrange(0,discrete_size)
		ay = random.randrange(0,discrete_size)

		current_pose[0] = ax
		current_pose[1] = ay

		simulated_observation_model()
		
		current_trajectory = [[current_pose[0], current_pose[1]]]
		current_observed_trajectory = [[observed_state[0],observed_state[1]]] 
		act_ind = optimal_policy[observed_state[0],observed_state[1]]
		current_actions_taken = [act_ind]
		state_counter=1
	
		while (state_counter<max_path_length)and(current_pose!=max_val_location):
			
			simulated_model(act_ind)
			simulated_observation_model()
			
			state_counter+=1

			current_trajectory.append([current_pose[0],current_pose[1]])
			current_observed_trajectory.append([observed_state[0],observed_state[1]])
			current_actions_taken.append(act_ind)

			print "Current Pose:", current_pose, "Action Index:", act_ind, "Action Taken:", action_space[act_ind], "Observed State:", observed_state
			act_ind = optimal_policy[observed_state[0],observed_state[1]]


		demo_counter+=1
		print demo_counter

		# current_actions_taken.remove(current_actions_taken[0])
		trajectories.append(current_trajectory)
		observed_trajectories.append(current_observed_trajectory)
		actions_taken.append(current_actions_taken)
		trajectory_lengths[demo_counter] = state_counter
		trajectory_lengths=trajectory_lengths.astype(int)
		# new_demo = raw_input("Do you want to start a new demonstration? ")

initialize_all()
follow_policy()

trajectories.remove(trajectories[0])
observed_trajectories.remove(observed_trajectories[0])
actions_taken.remove(actions_taken[0])

print "The Observed Trajectories are as follows:", observed_trajectories
print "The trajectories are as follows: ",trajectories
print "The trans mats are as follows:", trans_mat

with file('Trajectories.txt','w') as outfile:
	for data_slice in trajectories:
		outfile.write('# New slice\n')
		npy.savetxt(outfile,data_slice,fmt='%i')
		
with file('Observed_Trajectories.txt','w') as outfile: 
	for data_slice in observed_trajectories:
		outfile.write('#Observed Trajectory.\n')
		npy.savetxt(outfile,data_slice,fmt='%i')

with file('Actions_Taken.txt','w') as outfile:
	for data_slice in actions_taken:
		outfile.write('#Actions Taken.\n')
		npy.savetxt(outfile,data_slice,fmt='%i')