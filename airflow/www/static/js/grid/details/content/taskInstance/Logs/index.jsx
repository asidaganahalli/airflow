/*!
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

import React, { useRef, useState, useEffect } from 'react';
import {
  Text,
  Box,
  Flex,
  Divider,
  Code,
  Button,
  Checkbox,
} from '@chakra-ui/react';

import { getMetaValue } from '../../../../../utils';
import LogLink from './LogLink';
import useTaskLog from '../../../../api/useTaskLog';
import LinkButton from '../../../../components/LinkButton';

const showExternalLogRedirect = getMetaValue('show_external_log_redirect') === 'True';
const externalLogName = getMetaValue('external_log_name');
const logUrl = getMetaValue('log_url');

const getLinkIndexes = (tryNumber) => {
  const internalIndexes = [];
  const externalIndexes = [];

  [...Array(tryNumber + 1 || 0)].forEach((_, index) => {
    if (index === 0 && tryNumber < 2) return;
    const isExternal = index !== 0 && showExternalLogRedirect;
    if (isExternal) {
      externalIndexes.push(index);
    } else {
      internalIndexes.push(index);
    }
  });

  return [internalIndexes, externalIndexes];
};

const Logs = ({
  dagId,
  dagRunId,
  taskId,
  executionDate,
  tryNumber,
  isGroup,
}) => {
  const [internalIndexes, externalIndexes] = getLinkIndexes(tryNumber);
  const [selectedAttempt, setSelectedAttempt] = useState(1);
  const [shouldRequestFullContent, setShouldRequestFullContent] = useState(false);
  const { data, isSuccess } = useTaskLog({
    dagId,
    dagRunId,
    taskId,
    taskTryNumber: selectedAttempt,
    fullContent: shouldRequestFullContent,
    enabled: (!isGroup),
  });

  const codeBlockBottomDiv = useRef(null);

  useEffect(() => {
    if (codeBlockBottomDiv.current) {
      codeBlockBottomDiv.current.scrollIntoView({ behavior: 'smooth' });
    }
  });

  const params = new URLSearchParams({
    task_id: taskId,
    execution_date: executionDate,
  }).toString();

  return (
    <>
      {tryNumber > 0 && (
      <>
        <Text as="span"> (by attempts)</Text>
        <Box>
          <Flex my={1} justifyContent="space-between">
            <Flex flexWrap="wrap">
              {internalIndexes.map((index) => (
                <Button
                  key={index}
                  variant="ghost"
                  colorScheme="blue"
                  onClick={() => setSelectedAttempt(index)}
                >
                  {index}
                </Button>
              ))}
            </Flex>
            <Flex>
              <Checkbox
                onChange={() => setShouldRequestFullContent((previousState) => !previousState)}
                px={4}
              >
                <Text as="strong">Full Logs</Text>
              </Checkbox>
              <LogLink
                index={selectedAttempt}
                dagId={dagId}
                taskId={taskId}
                executionDate={executionDate}
                isInternal
              />
              <LinkButton
                href={`${logUrl}&${params}`}
              >
                See More
              </LinkButton>
            </Flex>
          </Flex>
        </Box>
        {
          isSuccess && (
            <Code
              height={350}
              overflowY="scroll"
              p={3}
              pb={0}
              display="block"
              whiteSpace="pre-wrap"
              border="1px solid"
              borderRadius={3}
              borderColor="blue.500"
            >
              {data}
              <div ref={codeBlockBottomDiv} />
            </Code>
          )
        }
      </>
      )}
      {externalLogName && externalIndexes.length > 0 && (
      <>
        <Box>
          <Text>
            View Logs in
            {' '}
            {externalLogName}
            {' '}
            (by attempts):
          </Text>
          <Flex flexWrap="wrap">
            {
              externalIndexes.map(
                (index) => (
                  <LogLink
                    key={index}
                    index={index}
                    dagId={dagId}
                    taskId={taskId}
                    executionDate={executionDate}
                  />
                ),
              )
            }
          </Flex>
        </Box>
        <Divider my={2} />
      </>
      )}
    </>
  );
};

export default Logs;
