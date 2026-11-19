(define (problem blocksworld)
	(:domain blocksworld)
	(:objects
		blue_1 - block
		blue_2 - block
		green_1 - block
		green_2 - block
		orange_1 - block
		orange_2 - block
		purple_1 - block
		purple_2 - block
		red_1 - block
		red_2 - block
		yellow_1 - block
		yellow_2 - block
		robot - robot
	)
	(:init (handempty robot)
		(ontable green_1)
		(on red_1 green_1)
		(on purple_1 red_1)
		(on blue_1 purple_1)
		(on yellow_1 blue_1)
		(clear yellow_1)

		(ontable blue_2)
		(clear blue_2)

		(ontable yellow_2)
		(clear yellow_2)

		(ontable red_2)
		(clear red_2)

		(ontable green_2)
		(clear green_2)

		(ontable orange_2)
		(clear orange_2)

		(ontable orange_1)
		(clear orange_1)

		(ontable purple_2)
		(clear purple_2)
	)
	(:goal (and (handempty robot)
		(ontable red_2)
		(on red_1 red_2)
		(on yellow_1 red_1)
		(clear yellow_1)

		(ontable purple_1)
		(on blue_1 purple_1)
		(clear blue_1)

		(ontable orange_2)
		(clear orange_2)

		(ontable orange_1)
		(on blue_2 orange_1)
		(on green_2 blue_2)
		(clear green_2)

		(ontable purple_2)
		(on green_1 purple_2)
		(on yellow_2 green_1)
		(clear yellow_2)
	))
)