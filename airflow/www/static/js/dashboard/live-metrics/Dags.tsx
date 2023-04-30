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

import React from "react";
import {
  Box,
  BoxProps,
  Card,
  CardBody,
  CardHeader,
  Flex,
  Heading,
  Spinner,
  Text,
} from "@chakra-ui/react";
import { useDags } from "src/api";

const Dags = (props: BoxProps) => {
  const { data: dataOnlyUnpaused, isSuccess: isSuccessUnpaused } = useDags({
    paused: false,
  });

  const { data, isSuccess } = useDags({});

  return (
    <Box {...props}>
      {isSuccess && isSuccessUnpaused ? (
        <Card>
          <CardHeader textAlign="center" p={3}>
            <Heading size="md">DAGs</Heading>
          </CardHeader>
          <CardBody>
            <Flex flexDirection="column" mb={5}>
              <Text as="b" color="blue.600">
                Number of unpaused DAGs:
              </Text>
              <Flex justifyContent="center" mt={2}>
                <Heading as="b" size="xl">
                  {dataOnlyUnpaused.totalEntries}
                </Heading>
              </Flex>
            </Flex>
            <Flex justifyContent="end" textAlign="right">
              <Text size="md" color="gray.600">
                on a total of <Text as="b">{data.totalEntries}</Text> DAGs
              </Text>
            </Flex>
          </CardBody>
        </Card>
      ) : (
        <Spinner color="blue.500" speed="1s" mr="4px" size="xl" />
      )}
    </Box>
  );
};

export default Dags;
