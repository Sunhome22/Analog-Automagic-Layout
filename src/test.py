





def main():
    grid = [[0 for _ in range(20)] for _ in range(20)]
    segment = [(10,10), (10,11), (10,12), (10,13),(10,14)]
    p =  0
    for x, y in segment:
        for i in range(-2,3):
            for p in range(-4, 5):
                grid[y + p][x + i] = 1

    for row in grid:
        print(row)



if __name__ == '__main__':
    main()

    def __run_multiple_astar_multiple_times(self, net):
        best_path = None
        best_length = float('inf')
        best_start = None
        path = []
        full_path = []
        if self.RUN_MULTIPLE_ASTAR:
            self.logger.info(f"Running A* multiple times for net: {net}")
            for start in self.goal_nodes:
                self.logger.info(f"Starting A* with start node: {start}")
                path, length =AstarAlgorithm(self.grid_vertical, self.grid_horizontal,start, self.goal_nodes,
                                      self.routing_parameters.minimum_segment_length).a_star()
                self.logger.info(f"Finished running A* with start node: {start}")

                if path is not None and length < best_length:
                    best_start = start
                    best_path = path
                    best_length = length
            self.logger.info(f"Best start for net: {net} is node: {best_start}")
            return best_path
        else:
            self.logger.info(f"Running A* one time for net: {net}")
            test_order = tsp_order_no_start(self.goal_nodes)
            self.logger.info(f"test_order = {test_order}")
            failed_connection = []
            connected_nodes = []
            for i in range(len(test_order)-1):





                print(self.goal_nodes[test_order[i]], [self.goal_nodes[test_order[i+1]]])
                path, _ = AstarAlgorithm(self.grid_vertical, self.grid_horizontal, self.goal_nodes[test_order[i]], [self.goal_nodes[test_order[i+1]]],
                             self.routing_parameters.minimum_segment_length).a_star()
                print(path)
                if path is None:
                    self.logger.error(f"No path found between {self.goal_nodes[test_order[i]]} and {self.goal_nodes[test_order[i+1]]}")
                    failed_connection.append((test_order[i], test_order[i+1]))
                if path is not None:
                    connected_nodes.append((test_order[i], test_order[i+1]))
                    full_path.extend(path)
            if len(failed_connection)>0:
                for failed_pair in failed_connection:
                    node1, node2 = failed_pair
                    new_goal, new_start = None, None
                    for connected_pair in connected_nodes:
                        connected_node, connected_node2 = connected_pair
                        if node1 == connected_node:
                            new_start = node2
                            new_goal = connected_node2
                        elif node1 == connected_node2:
                            new_goal = connected_node
                            new_start = node2
                        elif node2 == connected_node:
                            new_goal = connected_node2
                            new_start = node1
                        elif node2 == connected_node2:
                            new_goal = connected_node
                            new_start = node1



                        if new_start is not None and new_goal is not None:
                            path, _ = AstarAlgorithm(self.grid_vertical, self.grid_horizontal,
                                                     new_start,
                                                     [new_goal],
                                                     self.routing_parameters.minimum_segment_length).a_star()
                            if path is not None:
                                full_path.extend(path)
                                break

            return full_path