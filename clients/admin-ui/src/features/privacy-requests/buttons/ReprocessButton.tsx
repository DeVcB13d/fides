import { Box, Button, ButtonProps, forwardRef, Text } from "@fidesui/react";
import { useState } from "react";

import { useAppDispatch, useAppSelector } from "~/app/hooks";
import { getErrorMessage } from "~/features/common/helpers";
import { useAlert } from "~/features/common/hooks";

import {
  selectRetryRequests,
  setRetryRequests,
  useBulkRetryMutation,
  useRetryMutation,
} from "../privacy-requests.slice";
import { PrivacyRequest } from "../types";

type ReprocessButtonProps = {
  buttonProps?: ButtonProps;
  subjectRequest?: PrivacyRequest;
};

const ReprocessButton = forwardRef(
  ({ buttonProps, subjectRequest }: ReprocessButtonProps, ref) => {
    const dispatch = useAppDispatch();
    const [isReprocessing, setIsReprocessing] = useState(false);
    const { errorAlert, successAlert } = useAlert();

    const { errorRequests } = useAppSelector(selectRetryRequests);
    const [bulkRetry] = useBulkRetryMutation();
    const [retry] = useRetryMutation();

    const handleBulkReprocessClick = async () => {
      setIsReprocessing(true);
      const payload = await bulkRetry(errorRequests);
      if ("error" in payload) {
        dispatch(setRetryRequests({ checkAll: false, errorRequests: [] }));
        errorAlert(
          getErrorMessage(payload.error),
          `DSR batch automation has failed due to the following:`,
          { duration: null }
        );
      } else {
        if (payload.data.failed.length > 0) {
          errorAlert(
            <Box>
              DSR automation has failed for{" "}
              <Text as="span" fontWeight="semibold">
                {payload.data.failed.length}
              </Text>{" "}
              subject request(s). Please review the event log for further
              details.
            </Box>,
            undefined,
            { containerStyle: { maxWidth: "max-content" }, duration: null }
          );
        }
        if (payload.data.succeeded.length > 0) {
          successAlert(`Data subject request(s) are now being reprocessed.`);
        }
      }
      setIsReprocessing(false);
    };

    const handleSingleReprocessClick = async () => {
      if (!subjectRequest) {
        return;
      }
      setIsReprocessing(true);
      const payload = await retry(subjectRequest);
      if ("error" in payload) {
        errorAlert(
          getErrorMessage(payload.error),
          `DSR automation has failed for this subject request due to the following:`,
          { duration: null }
        );
      } else {
        successAlert(`Data subject request is now being reprocessed.`);
      }
      setIsReprocessing(false);
    };

    return (
      <Button
        {...buttonProps}
        isDisabled={isReprocessing}
        isLoading={isReprocessing}
        loadingText="Reprocessing"
        onClick={
          subjectRequest ? handleSingleReprocessClick : handleBulkReprocessClick
        }
        ref={ref}
        spinnerPlacement="end"
        variant="outline"
        _hover={{
          bg: "gray.100",
        }}
        _loading={{
          opacity: 1,
          div: { opacity: 0.4 },
        }}
      >
        Reprocess
      </Button>
    );
  }
);

export default ReprocessButton;
