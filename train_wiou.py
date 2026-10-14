"""
train_wiou.py - same training as train_yolo11m.py, with the box-regression loss replaced by Wise-IoU v3
(Tong et al., "Wise-IoU: Bounding Box Regression Loss with Dynamic Focusing Mechanism", arXiv 2301.10051, 2023),
the loss used by the CWB-YOLOv8 reference model in the synopsis.

    L_IoU   = 1 - IoU(b, b_gt)
    R_WIoU  = exp( ((x - x_gt)^2 + (y - y_gt)^2) / (W_g^2 + H_g^2)* )      W_g, H_g: smallest enclosing box, * = no grad
    beta    = L_IoU* / mean(L_IoU)                                          outlier degree (running mean, momentum 0.01)
    r       = beta / (delta * alpha^(beta - delta))                          non-monotonic focusing, alpha 1.9, delta 3
    L_WIoU  = r * R_WIoU * L_IoU

Low-quality boxes (large beta, e.g. ambiguous annotations) and already-easy boxes (small beta) get smaller gradients,
so training concentrates on ordinary-quality anchors. DFL loss and everything else is unchanged.

python train_wiou.py --data dataset_4cls/data_sqrt.yaml --name yolo11s_4cls_sqrt_wiou --model yolo11s.pt ...
(same flags as train_yolo11m.py)
"""
import torch
from ultralytics.utils import loss as L
from ultralytics.utils.metrics import bbox_iou

ALPHA, DELTA, MOMENTUM = 1.9, 3.0, 0.01
_state = {"mean": 1.0}
_orig_forward = L.BboxLoss.forward


def wiou_v3(pred, target):
    iou = bbox_iou(pred, target, xywh=False)                         # (n, 1)
    l_iou = 1.0 - iou
    cw = torch.max(pred[:, 2:3], target[:, 2:3]) - torch.min(pred[:, 0:1], target[:, 0:1])
    ch = torch.max(pred[:, 3:4], target[:, 3:4]) - torch.min(pred[:, 1:2], target[:, 1:2])
    dc = (((pred[:, :2] + pred[:, 2:]) - (target[:, :2] + target[:, 2:])) / 2) ** 2
    r_wiou = torch.exp(dc.sum(-1, keepdim=True) / (cw ** 2 + ch ** 2 + 1e-7).detach())
    if torch.is_grad_enabled() and l_iou.numel():
        _state["mean"] = (1 - MOMENTUM) * _state["mean"] + MOMENTUM * float(l_iou.detach().mean())
    beta = l_iou.detach() / max(_state["mean"], 1e-6)
    r = beta / (DELTA * torch.pow(torch.tensor(ALPHA, device=beta.device), beta - DELTA))
    return r * r_wiou * l_iou


def wiou_forward(self, pred_dist, pred_bboxes, anchor_points, target_bboxes, target_scores, target_scores_sum,
                 fg_mask, imgsz, stride):
    _, loss_dfl = _orig_forward(self, pred_dist, pred_bboxes, anchor_points, target_bboxes, target_scores,
                                target_scores_sum, fg_mask, imgsz, stride)        # DFL term unchanged
    weight = target_scores[fg_mask].sum(-1, keepdim=True)
    loss_iou = (wiou_v3(pred_bboxes[fg_mask], target_bboxes[fg_mask]) * weight).sum() / target_scores_sum
    return loss_iou, loss_dfl


L.BboxLoss.forward = wiou_forward

if __name__ == "__main__":
    print("box loss: Wise-IoU v3 (alpha 1.9, delta 3, momentum 0.01)")
    import train_yolo11m
    train_yolo11m.main()
