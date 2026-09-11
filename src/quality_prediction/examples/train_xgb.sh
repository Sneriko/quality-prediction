qp-train-xgb \
  --train-csv  \
  --model-dir  \
  --log-dir  \
  --feature-analysis-dir  \
  --n-trials-full 100 \
  --n-trials-baseline 30 \
  --feature-selection \
  --feature-sets single_htr_line_score_mean,confidence_only,json_model_only,image_only,dit_only,ngram_only,lexical_only,full \
  --targets target_bow_f1,target_bow_precision,target_bow_recall,target_iou50_line_f1,target_iou50_line_precision,target_iou50_line_recall,target_map50_line,target_map50_region \
