import unittest

from ament_index_python.packages import get_package_share_directory
import launch
import launch.actions
import launch_ros.actions
import launch_testing
import rclpy
from rclpy.node import Node
from rclpy.task import Future

from std_msgs.msg import String


def generate_test_description():
    config = get_package_share_directory('network_bridge') + '/config/'
    return launch.LaunchDescription([
        launch_ros.actions.Node(
            package='network_bridge',
            executable='network_bridge',
            name='udp1',
            output='screen',
            parameters=[config + 'Udp1.yaml'],
            arguments=['--ros-args', '--log-level',
                       'debug', '--log-level', 'rcl:=info'],
        ),
        launch_ros.actions.Node(
            package='network_bridge',
            executable='network_bridge',
            name='udp2',
            output='screen',
            parameters=[config + 'Udp2.yaml'],
            arguments=['--ros-args', '--log-level',
                       'debug', '--log-level', 'rcl:=info'],
        ),
        launch_testing.actions.ReadyToTest()
    ])


class UdpWildcardTestNode(Node):
    def __init__(self):
        super().__init__('wildcard_test_node')
        self.test_message_received = Future()
        self.received_msg = None
        self.publisher = self.create_publisher(
            String, '/udp1/MyWildcard/dynamic/data', 10)
        self.subscriber = self.create_subscription(
            String, '/udp2/MyWildcard/dynamic/data',
            self.listener_callback, 10)
        self.timer = self.create_timer(0.1, self.publish)

    def publish(self):
        msg = String()
        msg.data = 'Wildcard123'
        self.publisher.publish(msg)

    def listener_callback(self, msg):
        self.received_msg = msg
        if not self.test_message_received.done():
            self.test_message_received.set_result(True)


class TestUdpWildcard(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()

    def test_node_output(self, proc_output):
        proc_output.assertWaitFor('Topic pattern: /MyWildcard/*/data', timeout=5.0)
        proc_output.assertWaitFor('Setting up local endpoint', timeout=5.0)

        # Topic is created after the bridges start, so it must be discovered
        node = UdpWildcardTestNode()

        try:
            rclpy.spin_until_future_complete(
                node, node.test_message_received, timeout_sec=10.0)
            self.assertTrue(
                node.test_message_received.done(),
                'Timeout on message receival.')
            self.assertEqual(
                node.received_msg.data,
                'Wildcard123',
                'The received message did not match the expected output.')
        finally:
            node.destroy_node()


if __name__ == '__main__':
    launch_testing.main()
