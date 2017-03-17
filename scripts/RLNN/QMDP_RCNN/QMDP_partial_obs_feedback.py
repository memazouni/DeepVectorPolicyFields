#!/usr/bin/env python
import numpy as npy
from variables import *

def initialize_state():
	# global current_pose, from_state_belief, observed_state
	global observed_state, obs_space, h, observation_model, from_state_belief
	
	from_state_belief = npy.zeros((discrete_size,discrete_size))
	from_state_belief[observed_state[0],observed_state[1]] = 1.

	# for i in range(-h,h+1):
	# 	for j in range(-h,h+1):
	# 		from_state_belief[observed_state[0]+i,observed_state[1]+j] = observation_model[h+i,h+j]

def initialize_observation():
	global observation_model
	# observation_model = npy.array([[0.05,0.05,0.05],[0.05,0.6,0.05],[0.05,0.05,0.05]])
	observation_model = npy.array([[0.05,0.1,0.05],[0.1,1,0.1],[0.05,0.1,0.05]])

	epsilon=0.0001
	observation_model += epsilon
	observation_model /= observation_model.sum()

def display_beliefs():
	global from_state_belief,to_state_belief,current_pose

	print "From:"
	for i in range(observed_state[0]-5,observed_state[0]+5):
		print from_state_belief[i,observed_state[1]-5:observed_state[1]+5]
	
	print "To:"
	for i in range(observed_state[0]-5,observed_state[0]+5):
		print to_state_belief[i,observed_state[1]-5:observed_state[1]+5]

	print "Corrected:"
	for i in range(observed_state[0]-5,observed_state[0]+5):
		print corr_to_state_belief[i,observed_state[1]-5:observed_state[1]+5]

def bayes_obs_fusion():
	global to_state_belief, current_pose, observation_model, obs_space, observed_state, corr_to_state_belief
	
	
	h = obs_space/2
	intermediate_belief = npy.zeros((discrete_size+2*h,discrete_size+2*h))
	ext_to_bel = npy.zeros((discrete_size+2*h,discrete_size+2*h))
	ext_to_bel[h:discrete_size+h,h:discrete_size+h] = copy.deepcopy(to_state_belief[:,:])

	for i in range(-h,h+1):
		for j in range(-h,h+1):
			intermediate_belief[h+observed_state[0]+i,h+observed_state[1]+j] = ext_to_bel[h+observed_state[0]+i,h+observed_state[1]+j] * observation_model[h+i,h+j]
	
	# corr_to_state_belief[:,:] = copy.deepcopy(intermediate_belief[:,:])
	corr_to_state_belief[:,:] = copy.deepcopy(intermediate_belief[h:h+discrete_size,h:h+discrete_size])
	corr_to_state_belief /= corr_to_state_belief.sum()

	if (intermediate_belief.sum()==0):
		print "Something's wrong."
		display_beliefs()
		print npy.unravel_index(from_state_belief.argmax(),from_state_belief.shape)

def initialize_all():
	initialize_observation()
	initialize_state()

def construct_from_ext_state():
	global from_state_ext, from_state_belief,discrete_size
	d=discrete_size
	from_state_ext[w:d+w,w:d+w] = copy.deepcopy(from_state_belief[:,:])

def belief_prop_extended(action_index):
	global trans_mat, from_state_ext, to_state_ext, w, discrete_size
	to_state_ext = signal.convolve2d(from_state_ext,trans_mat[action_index],'same')
	d=discrete_size
	##NOW MUST FOLD THINGS:
	for i in range(0,2*w):
		to_state_ext[i+1,:]+=to_state_ext[i,:]
		to_state_ext[i,:]=0
		to_state_ext[:,i+1]+=to_state_ext[:,i]
		to_state_ext[:,i]=0
		to_state_ext[d+2*w-i-2,:]+= to_state_ext[d+2*w-i-1,:]
		to_state_ext[d+2*w-i-1,:]=0
		to_state_ext[:,d+2*w-i-2]+= to_state_ext[:,d+2*w-i-1]
		to_state_ext[:,d+2*w-i-1]=0

	to_state_belief[:,:] = copy.deepcopy(to_state_ext[w:d+w,w:d+w])

def calc_softmax():
	global qmdp_values, qmdp_values_softmax

	for act in range(0,action_size):
		qmdp_values_softmax[act] = npy.exp(qmdp_values[act]) / npy.sum(npy.exp(qmdp_values), axis=0)

def update_QMDP_values():
	global to_state_belief, q_value_estimate, qmdp_values, from_state_belief

	for act in range(0,action_size):
		# qmdp_values[act] = npy.sum(q_value_estimate[act]*to_state_belief)
		qmdp_values[act] = npy.sum(q_value_estimate[act]*from_state_belief)

# # def IRL_backprop():
# def Q_backprop():
# 	global to_state_belief, q_value_estimate, qmdp_values_softmax, learning_rate, annealing_rate
# 	global trajectory_index, length_index, target_actions, time_index

# 	update_QMDP_values()
# 	calc_softmax()
 
# 	alpha = learning_rate - annealing_rate * time_index

# 	for act in range(0,action_size):
# 		q_value_estimate[act,:,:] -= alpha*(qmdp_values_softmax[act]-target_actions[act])*from_state_belief[:,:]

def reward_backprop():
	global reward_estimate, qmdp_values_softmax, target_actions, from_state_belief
	global time_index

	update_QMDP_values()
	calc_softmax()

	# alpha = learning_rate - annealing_rate*time_index
	alpha = learning_rate

	for act in range(0,action_size):
		reward_estimate[act,:,:] -= alpha * (qmdp_values_softmax[act]-target_actions[act]) * from_state_belief[:,:]

def belief_prop(traj_ind,len_ind):
	construct_from_ext_state()
	belief_prop_extended(actions_taken[traj_ind,len_ind])

def parse_data(traj_ind,len_ind):
	global observed_state, trajectory_index, length_index, target_actions, current_pose, trajectories

	observed_state[:] = observed_trajectories[traj_ind,len_ind+1,:]
	# observed_state[:] = trajectories[traj_ind,len_ind+1,:]
	target_actions[:] = 0
	target_actions[actions_taken[traj_ind,len_ind]] = 1
	current_pose[:] = trajectories[traj_ind,len_ind,:]

def feedforward_recurrence():
	global from_state_belief, to_state_belief, corr_to_state_belief
	from_state_belief = copy.deepcopy(corr_to_state_belief)
	# from_state_belief = copy.deepcopy(to_state_belief)

def update_q_estimate():
	global reward_estimate, q_value_estimate
	q_value_estimate = reward_estimate + q_value_layers

def max_pool():
	global q_value_estimate, value_function
	value_function = npy.amax(q_value_estimate, axis=0)

def conv_layer():	
	global value_function, q_value_layers
	trans_mat_flip = copy.deepcopy(trans_mat)

	for act in range(0,action_size):		
		#Convolve with each transition matrix.
		# action_value_layers[act]=signal.convolve2d(value_function,trans_mat[act],'same','fill',0)
		trans_mat_flip[act] = npy.flipud(npy.fliplr(trans_mat[act]))
		q_value_layers[act]=signal.convolve2d(value_function,trans_mat_flip[act],'same','fill',0)

def master(traj_ind, len_ind):
	global to_state_belief, from_state_belief, current_pose
	global trajectory_index, length_index

	parse_data(traj_ind,len_ind)
	belief_prop(traj_ind,len_ind)
	bayes_obs_fusion()
	reward_backprop()
	update_q_estimate()
	feedforward_recurrence()	

	# print "OS:", observed_state, "CP:", current_pose, "TA:", target_actions, "SM:", qmdp_values_softmax

def feedback():
	max_pool()
	conv_layer()

def Inverse_Q_Learning():
	global trajectories, trajectory_index, length_index, trajectory_length, number_trajectories, time_index, from_state_belief
	time_index = 0
	
	for trajectory_index in range(0,number_trajectories):
	# for trajectory_index in range(0,25):
		
		parse_data(trajectory_index,0)
		initialize_state()

		for length_index in range(0,trajectory_length-1):			
			
			if (from_state_belief.sum()>0):
				master(trajectory_index, length_index)
				time_index += 1
				print "Trajectory:", trajectory_index, "Step:", length_index
			else: 
				print "WARNING: Belief sum below 0."
				print "Trajectory: ", trajectory_index, "Step:", length_index

		feedback()

		# imshow(q_value_estimate[0], interpolation='nearest', origin='lower', extent=[0,50,0,50], aspect='auto')
		# # plt.show(block=False)
		# colorbar()
		# plt.show()
		# # plt.title('Trajectory Index: %i')
		# # draw()
		# # show() 

parse_data(0,0)
initialize_all()
Inverse_Q_Learning()

# for i in range(0,action_size):
# 	imshow(reward_estimate[i], interpolation='nearest', origin='lower', extent=[0,50,0,50], aspect='auto')
# 	colorbar()
# 	plt.show()

with file('Q_Value_Estimate.txt','w') as outfile:
	for data_slice in q_value_estimate:
		outfile.write('#Q_Value_Estimate.\n')
		npy.savetxt(outfile,data_slice,fmt='%-7.2f')

with file('Value_Function_Estimate.txt','w') as outfile:
	outfile.write('#Value_Function_Estimate.\n')
	npy.savetxt(outfile,value_function,fmt='%-7.2f')

with file('Reward_Function_Estimate.txt','w') as outfile:
	for data_slice in reward_estimate:
		outfile.write('#Reward_Function_Estimate.\n')
		npy.savetxt(outfile,data_slice,fmt='%-7.2f')

