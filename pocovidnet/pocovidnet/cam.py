import numpy as np
import cv2
import tensorflow.keras as K


def get_class_activation_map(
    model,
    img: np.array,
    class_id: int,
    layer_name: str = 'block5_conv3',
    return_map: bool = False,
    size: tuple = (224, 224),
    zeroing: float = 0.5,
    heatmap_weight: float = 0.25
):
    """
    Receives a model, an image and a class ID and returns the CAM overlaying
    the image

    Arguments:
        model {[type]} -- Keras model object. Should have no nonlinearities and
            only single dense layer after the last convolution
        img {[type]} -- Input image for CAM computation
            image must be (1, 224, 224, 3) and values between 0 and 1.0
        class_id {[type]} -- ID of class for which CAM is computed
        return_map --  Whether the heatmap is returned in addition to the image
            overlayed with the heatmap.
        size -- Input size of the image
        zeroing -- Threshold between 0 and 1. Areas with a score below will be
            zeroed in the heatmap.
        heatmap_weight -- float used to weight heatmap when added to image.

    Keyword Arguments:
        layer_name {str} -- [description] (default: {'block5_conv3'})

    Returns:
        [type] -- [description]
    """

    if len(img.shape) == 3:
        img = np.expand_dims(img, 0)
    if img.shape[1] == 3:
        img = img.transpose(0, 2, 3, 1)
    if img.shape[1:3] != size:
        raise ValueError(f'Img has size {img.shape}, should have {size}.')
    # In the CAM case, second to last layer is used
    class_weights = model.layers[-1].get_weights()[0]
    final_conv_layer = get_output_layer(model, layer_name)
    get_output = K.backend.function(
        [model.layers[0].input],
        [final_conv_layer.output, model.layers[-1].output]
    )
    [conv_outputs, predictions] = get_output(img)
    # print(predictions, np.max(img), img.shape)
    conv_outputs = conv_outputs[0, :, :, :]
    if np.max(img) <= 1:
        img = (img * 255).astype(int)

    #Create the class activation map.
    cam = np.zeros(dtype=np.float32, shape=conv_outputs.shape[0:2])
    for i, w in enumerate(class_weights[:, class_id]):
        cam += w * conv_outputs[:, :, i]
    cam /= np.max(cam)
    cam = cv2.resize(cam, size)
    heatmap = cv2.applyColorMap(np.uint8(255 * cam), cv2.COLORMAP_JET)
    heatmap[np.where(cam < zeroing)] = 0
    img = np.clip(heatmap * heatmap_weight + img, 0, 255)
    if return_map:
        return img[0, :, :, :], heatmap
    else:
        return img[0, :, :, :]


def get_output_layer(model, layer_name):
    # get the symbolic outputs of each "key" layer (we gave them unique names).
    layer_dict = dict([(layer.name, layer) for layer in model.layers])
    layer = layer_dict[layer_name]
    return layer
