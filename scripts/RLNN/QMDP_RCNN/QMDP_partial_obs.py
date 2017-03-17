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
	
	intermediate_belief = npy.zeros((discrete_size,discrete_size))
	h = obs_space/2
	for i in range(-h,h+1):
		for j in range(-h,h+1):
			intermediate_belief[observed_state[0]+i,observed_state[1]+j] = to_state_belief[observed_state[0]+i,observed_state[1]+j] * observation_model[h+i,h+j]
	
	corr_to_state_belief[:,:] = copy.deepcopy(intermediate_belief[:,:])
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

# def IRL_backprop():
def Q_backprop():
	global to_state_belief, q_value_estimate, qmdp_values_softmax, learning_rate, annealing_rate
	global trajectory_index, length_index, target_actions, time_index

	update_QMDP_values()
	calc_softmax()
 
	alpha = learning_rate - annealing_rate * time_index

	for act in range(0,action_size):
		q_value_estimate[act,:,:] -= alpha*(qmdp_values_softmax[act]-target_actions[act])*from_state_belief[:,:]

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

def master(traj_ind, len_ind):
	global to_state_belief, from_state_belief, current_pose
	global trajectory_index, length_index

	parse_data(traj_ind,len_ind)
	belief_prop(traj_ind,len_ind)
	bayes_obs_fusion()
	Q_backprop()
	feedforward_recurrence()	

	print "OS:", observed_state, "CP:", current_pose, "TA:", target_actions, "SM:", qmdp_values_softmax

def Inverse_Q_Learning():
	global trajectories, trajectory_index, length_index, trajectory_length, number_trajectories, time_index, from_state_belief
	time_index = 0
	
	for trajectory_index in range(0,number_trajectories):
	# for trajectory_index in range(0,3):
		
		parse_data(trajectory_index,0)
		initialize_state()

		for length_index in range(0,trajectory_length-1):			
			
			if (from_state_belief.sum()>0):
				master(trajectory_index, length_index)
				time_index += 1
				print "Time index: ", time_index, "Trajectory:", trajectory_index, "Step:", length_index
			else: 
				print "WARNING: Belief sum below 0."
				print "Time index: ", time_index, "Trajectory: ", trajectory_index, "Step:", length_index

		# imshow(q_value_estimate[0], interpolation='nearest', origin='lower', extent=[0,50,0,50], aspect='auto')
		# # plt.show(block=False)
		# plt.show()
		# # plt.title('Trajectory Index: %i')
		# # colorbar()
		# # draw()
		# # show() 

parse_data(0,0)
initialize_all()
Inverse_Q_Learning()

with file('Q_Value_Estimate.txt','w') as outfile:
	for data_slice in q_value_estimate:
		outfile.write('#Q_Value_Estimate.\n')
		npy.savetxt(outfile,data_slice,fmt='%-7.2f')