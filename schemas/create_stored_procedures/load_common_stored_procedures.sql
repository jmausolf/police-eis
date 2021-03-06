/*
Function for using the model group table. This function requires a table like
-----------
CREATE TABLE results.model_groups
(
  model_group_id    SERIAL PRIMARY KEY,
  model_type        TEXT,
  model_parameters  JSONB,
  prediction_window TEXT,
  feature_list      TEXT []
);
-----------
A call like:
-----------
SELECT
  get_model_group_id(model_type, model_parameters, (config -> 'prediction_window') :: TEXT,
                     ARRAY(SELECT jsonb_array_elements_text(config -> 'officer_features')
                           ORDER BY 1) :: TEXT []),
  *
FROM results.models;
-----------
populates the table and returns the IDs
*/
CREATE OR REPLACE FUNCTION get_model_group_id(in_model_type        TEXT, in_model_parameters JSONB,
                                              in_prediction_window TEXT,
                                              in_feature_list      TEXT [])
  RETURNS INTEGER AS
$BODY$
DECLARE
  model_group_return_id INTEGER;
BEGIN
  --Obtain an advisory lock on the table to avoid double execution
  PERFORM pg_advisory_lock(60637);

  -- Check if the model_group_id exists, if not insert the model parameters and return the new value
  SELECT *
  INTO model_group_return_id
  FROM results.model_groups
  WHERE
    model_type = in_model_type AND model_parameters = in_model_parameters AND prediction_window = in_prediction_window
    AND feature_list = ARRAY(Select unnest(in_feature_list) ORDER BY 1);
  IF NOT FOUND
  THEN
    INSERT INTO results.model_groups (model_group_id, model_type, model_parameters, prediction_window, feature_list)
    VALUES (DEFAULT, in_model_type, in_model_parameters, in_prediction_window, ARRAY(Select unnest(in_feature_list) ORDER BY 1))
    RETURNING model_group_id
      INTO model_group_return_id;
  END IF;

  -- Release the lock again
  PERFORM pg_advisory_unlock(60637);


  RETURN model_group_return_id;
END;

$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;


