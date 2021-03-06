import os.path
import tensorflow as tf
import helper
import warnings
from distutils.version import LooseVersion
import project_tests as tests
import math
from glob import glob
from sklearn.model_selection import train_test_split

# Check TensorFlow Version
assert LooseVersion(tf.__version__) >= LooseVersion('1.0'), 'Please use TensorFlow version 1.0 or newer.  You are using {}'.format(tf.__version__)
print('TensorFlow Version: {}'.format(tf.__version__))

# Check for a GPU
if not tf.test.gpu_device_name():
    warnings.warn('No GPU found. Please use a GPU to train your neural network.')
else:
    print('Default GPU Device: {}'.format(tf.test.gpu_device_name()))

FREEZE_WEIGHTS = True
EPOCHS = 10
BATCH_SIZE = 4
KEEP_PROB_FREEZE = 1.0
KEEP_PROB = 1.0
LEARNING_RATE = 0.0003

def load_vgg(sess, vgg_path):
    """
    Load Pretrained VGG Model into TensorFlow.
    :param sess: TensorFlow Session
    :param vgg_path: Path to vgg folder, containing "variables/" and "saved_model.pb"
    :return: Tuple of Tensors from VGG model (image_input, keep_prob, layer3_out, layer4_out, layer7_out)
    """
    # TODO: Implement function
    #   Use tf.saved_model.loader.load to load the model and weights
    
    vgg_tag = 'vgg16'
    
    tf.saved_model.loader.load(sess, [vgg_tag], vgg_path)
    
    vgg_input_tensor_name = 'image_input:0'
    vgg_keep_prob_tensor_name = 'keep_prob:0'
    vgg_layer3_out_tensor_name = 'layer3_out:0'
    vgg_layer4_out_tensor_name = 'layer4_out:0'
    vgg_layer7_out_tensor_name = 'layer7_out:0'
    
    vgg = tf.get_default_graph()
    vgg_input = vgg.get_tensor_by_name(vgg_input_tensor_name)
    vgg_keep_prob = vgg.get_tensor_by_name(vgg_keep_prob_tensor_name)
    vgg_layer3 = vgg.get_tensor_by_name(vgg_layer3_out_tensor_name)
    vgg_layer4 = vgg.get_tensor_by_name(vgg_layer4_out_tensor_name)
    vgg_layer7 = vgg.get_tensor_by_name(vgg_layer7_out_tensor_name)
    
    return vgg_input, vgg_keep_prob, vgg_layer3, vgg_layer4, vgg_layer7
#tests.test_load_vgg(load_vgg, tf)

def layers(vgg_layer3_out, vgg_layer4_out, vgg_layer7_out, num_classes, keep_prob):
    """
    Create the layers for a fully convolutional network.  Build skip-layers using the vgg layers.
    :param vgg_layer3_out: TF Tensor for VGG Layer 3 output
    :param vgg_layer4_out: TF Tensor for VGG Layer 4 output
    :param vgg_layer7_out: TF Tensor for VGG Layer 7 output
    :param num_classes: Number of classes to classify
    :return: The Tensor for the last layer of output
    """
    # TODO: Implement function
    global FREEZE_WEIGHTS
    
    if FREEZE_WEIGHTS:
        vgg_layer7_out = tf.stop_gradient(vgg_layer7_out)
        vgg_layer4_out = tf.stop_gradient(vgg_layer4_out)
        vgg_layer3_out = tf.stop_gradient(vgg_layer3_out)
    
    conv_1x1_layer4 = tf.layers.conv2d(vgg_layer4_out, num_classes, kernel_size=(1, 1), strides=(1, 1), padding='same', name="transpose_conv_1x1_layer4", activation=tf.nn.relu, kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3), kernel_initializer=tf.truncated_normal_initializer(stddev=0.01))
    conv_1x1_layer3 = tf.layers.conv2d(vgg_layer3_out, num_classes, kernel_size=(1, 1), strides=(1, 1), padding='same', name="transpose_conv_1x1_layer3", activation=tf.nn.relu, kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3), kernel_initializer=tf.truncated_normal_initializer(stddev=0.01))
    
    vgg_layer7_transpose = tf.layers.conv2d_transpose(vgg_layer7_out, num_classes, kernel_size=(3, 3), strides=(2, 2), padding='same', name="transpose_vgg_layer7", activation=tf.nn.relu, kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3), kernel_initializer=tf.truncated_normal_initializer(stddev=0.01))
    vgg_layer7_transpose_dropout = tf.nn.dropout(vgg_layer7_transpose, keep_prob=keep_prob)
    
    vgg_skip_layer4 = tf.add(vgg_layer7_transpose_dropout, conv_1x1_layer4)
    vgg_layer4_transpose = tf.layers.conv2d_transpose(vgg_skip_layer4, num_classes, kernel_size=(3, 3), strides=(2, 2), padding='same', name="transpose_vgg_layer4", activation=tf.nn.relu, kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3), kernel_initializer=tf.truncated_normal_initializer(stddev=0.01))
    vgg_layer4_transpose_dropout = tf.nn.dropout(vgg_layer4_transpose, keep_prob=keep_prob)

    vgg_skip_layer3 = tf.add(vgg_layer4_transpose_dropout, conv_1x1_layer3)
    vgg_layer3_transpose = tf.layers.conv2d_transpose(vgg_skip_layer3, num_classes, kernel_size=(16, 16), strides=(8, 8), padding='same', name="transpose_vgg_layer3", activation=tf.nn.relu, kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3), kernel_initializer=tf.truncated_normal_initializer(stddev=0.01))
    
    return vgg_layer3_transpose
#tests.test_layers(layers)


def optimize(nn_last_layer, correct_label, learning_rate, num_classes):
    """
    Build the TensorFLow loss and optimizer operations.
    :param nn_last_layer: TF Tensor of the last layer in the neural network
    :param correct_label: TF Placeholder for the correct label image
    :param learning_rate: TF Placeholder for the learning rate
    :param num_classes: Number of classes to classify
    :return: Tuple of (logits, train_op, cross_entropy_loss)
    """
    # TODO: Implement function
    global FREEZE_WEIGHTS
    
    softmax = tf.nn.softmax_cross_entropy_with_logits(logits=nn_last_layer, labels=correct_label)
    cross_entropy = tf.reduce_mean(softmax, name="cross_entropy")
    
    logits = tf.reshape(nn_last_layer, (-1, num_classes))
    label = tf.reshape(correct_label, (-1, num_classes))
    prediction = tf.equal(tf.argmax(logits, 1), tf.argmax(label, 1))
    accuracy_operation = tf.reduce_mean(tf.cast(prediction, tf.float32), name="accuracy_operation")

    optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate)
    update_operations = tf.get_collection(tf.GraphKeys.UPDATE_OPS)

    if FREEZE_WEIGHTS:
        trainable_variables = []
        for variable in tf.trainable_variables():
            if any([sub_string in variable.name for sub_string in ['transpose_conv_1x1', 'beta', 'transpose_vgg', 'Adam']]):
                trainable_variables.append(variable)
            #print(variable.name)
        #print('number of trainable variables: ', len(tf.trainable_variables()))
        with tf.control_dependencies(update_operations):
            training_operation = optimizer.minimize(cross_entropy, var_list=trainable_variables, name="training_operation")
    else:
        with tf.control_dependencies(update_operations):
            training_operation = optimizer.minimize(cross_entropy, name="training_operation")

    return logits, training_operation, cross_entropy, accuracy_operation
#tests.test_optimize(optimize)


#def train_nn(sess, epochs, batch_size, get_batches_fn, train_op, cross_entropy_loss, input_image,
#             correct_label, keep_prob, learning_rate):
def train_nn(sess, epochs, batch_size, train_op, accuracy_operation, cross_entropy_loss, input_image,
             correct_label, keep_prob_freeze, keep_prob, learning_rate, training_image_paths, validation_image_paths, data_dir, image_shape):
    """
    Train neural network and print out the loss during training.
    :param sess: TF Session
    :param epochs: Number of epochs
    :param batch_size: Batch size
    :param get_batches_fn: Function to get batches of training data.  Call using get_batches_fn(batch_size)
    :param train_op: TF Operation to train the neural network
    :param cross_entropy_loss: TF Tensor for the amount of loss
    :param input_image: TF Placeholder for input images
    :param correct_label: TF Placeholder for label images
    :param keep_prob: TF Placeholder for dropout keep probability
    :param learning_rate: TF Placeholder for learning rate
    """
    # TODO: Implement function
    
    global KEEP_PROB
    global LEARNING_RATE
    
    training_losses = []
    training_accuracies = []
    validation_losses = []
    validation_accuracies = []
    
    get_batches_fn = helper.gen_batch_function(os.path.join(data_dir, 'data_road/training'), image_shape)
    
    for epoch in range(epochs):
        for (X, y) in get_batches_fn(batch_size, training_image_paths):
            loss, accuracy = sess.run([cross_entropy_loss, train_op], feed_dict={
                input_image: X,
                correct_label: y,
                keep_prob_freeze: KEEP_PROB_FREEZE,
                keep_prob: KEEP_PROB,
                learning_rate: LEARNING_RATE
            })
        
        training_loss = 0
        training_accuracy = 0
        for X, y in get_batches_fn(batch_size, training_image_paths):
            loss, accuracy = sess.run([cross_entropy_loss, accuracy_operation], feed_dict={input_image: X, correct_label: y,
                                                                     keep_prob_freeze: 1.0, keep_prob: 1.0})
            training_loss += (loss * X.shape[0])
            training_accuracy += (accuracy * X.shape[0])
        
        training_loss = training_loss/(int(math.floor(len(training_image_paths)/batch_size)*batch_size))
        training_accuracy = training_accuracy/(int(math.floor(len(training_image_paths)/batch_size)*batch_size))
        training_losses.append(training_loss)
        training_accuracies.append(training_accuracy)
        
        validation_loss = 0
        validation_accuracy = 0
        for X, y in get_batches_fn(batch_size, validation_image_paths):
            loss, accuracy = sess.run([cross_entropy_loss, accuracy_operation], feed_dict={input_image: X, correct_label: y,
                                                                     keep_prob_freeze: 1.0, keep_prob: 1.0})
            validation_loss += (loss * X.shape[0])
            validation_accuracy += (accuracy * X.shape[0])
        
        validation_loss = validation_loss/(int(math.floor(len(validation_image_paths)/batch_size)*batch_size))
        validation_accuracy = validation_accuracy/(int(math.floor(len(validation_image_paths)/batch_size)*batch_size))
        validation_losses.append(validation_loss)
        validation_accuracies.append(validation_accuracy)

        print(
            "Epoch %d:" % (epoch + 1),
            "Training loss: %.4f, accuracy: %.2f" % (training_loss, training_accuracy),
            "Validation loss: %.4f, accuracy: %.2f" % (validation_loss, validation_accuracy)
        )
#tests.test_train_nn(train_nn)


def run():
    
    global FREEZE_WEIGHTS
    global EPOCHS
    global BATCH_SIZE
    
    num_classes = 2
    image_shape = (160, 576)
    data_dir = './data'
    runs_dir = './runs'
    tests.test_for_kitti_dataset(data_dir)

    # Download pretrained vgg model
    helper.maybe_download_pretrained_vgg(data_dir)

    # OPTIONAL: Train and Inference on the cityscapes dataset instead of the Kitti dataset.
    # You'll need a GPU with at least 10 teraFLOPS to train on.
    #  https://www.cityscapes-dataset.com/

    with tf.Session() as sess:
        # Path to vgg model
        vgg_path = os.path.join(data_dir, 'vgg')
        # Create function to get batches
        #get_batches_fn = helper.gen_batch_function(os.path.join(data_dir, 'data_road/training'), image_shape)

        # OPTIONAL: Augment Images for better results
        #  https://datascience.stackexchange.com/questions/5224/how-to-prepare-augment-images-for-neural-network

        # TODO: Build NN using load_vgg, layers, and optimize function
        data_folder = os.path.join(data_dir, 'data_road/training')
        image_paths = glob(os.path.join(data_folder, 'image_2', '*.png'))

        training_image_paths, validation_image_paths = train_test_split(image_paths, test_size=0.2)

        # TODO: Train NN using the train_nn function
        vgg_input, vgg_keep_prob_freeze, vgg_layer3, vgg_layer4, vgg_layer7 = load_vgg(sess, vgg_path)
        output_layer = layers(vgg_layer3, vgg_layer4, vgg_layer7, num_classes, vgg_keep_prob_freeze)
        label = tf.placeholder(tf.int8, (None,) + image_shape + (num_classes,), name="label")
        learning_rate = tf.placeholder(tf.float32, [], name="learning_rate")
        vgg_keep_prob = tf.placeholder(tf.float32, [], name="keep_prob_new")
        output_layer, training_operation, cross_entropy, accuracy_operation = optimize(output_layer, label, learning_rate,
                                                                           num_classes)
        if FREEZE_WEIGHTS:
            variable_initializers = [variable.initializer for variable in tf.global_variables() if "transpose_conv_1x1" in variable.name or 'beta' in variable.name or "transpose_vgg" in variable.name or "Adam" in variable.name]
            sess.run(variable_initializers)
        else:
            sess.run(tf.global_variables_initializer())
        
        train_nn(sess, EPOCHS, BATCH_SIZE, training_operation, accuracy_operation, cross_entropy, vgg_input,
             label, vgg_keep_prob_freeze, vgg_keep_prob, learning_rate, training_image_paths, validation_image_paths, data_dir, image_shape)

        # TODO: Save inference data using helper.save_inference_samples
        #  helper.save_inference_samples(runs_dir, data_dir, sess, image_shape, logits, keep_prob, input_image)
        helper.save_inference_samples(runs_dir=runs_dir, data_dir=data_dir, sess=sess,image_shape=image_shape,
                                      logits=output_layer, keep_prob_freeze=vgg_keep_prob_freeze, keep_prob=vgg_keep_prob, 
                                      input_image=vgg_input)
        # OPTIONAL: Apply the trained model to a video

if __name__ == '__main__':
    
    run()
